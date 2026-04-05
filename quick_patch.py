import html
import os
import pathlib
import subprocess
import tempfile
import urllib.parse

from wsgiref.simple_server import make_server


class Repo:
    repo = pathlib.Path(os.environ["REPO"])
    branch = os.environ["DEFAULT_BRANCH"]

    def get_file(self, path):
        return subprocess.run(
            ["git", f"--git-dir={self.repo}", "show", f"{self.branch}:{path}"],
            check=True,
            stdout=subprocess.PIPE,
            encoding="UTF8",
        ).stdout

    def make_patch(self, path, patched, author, message):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = pathlib.Path(tempdir)
            subprocess.run(
                ["git", f"--git-dir={self.repo}", "worktree", "add", tempdir],
                check=True,
            )
            try:
                (tempdir / path).write_text(patched)
                subprocess.run(
                    ["git", "add", "."],
                    check=True,
                    encoding="UTF8",
                    cwd=tempdir,
                )
                subprocess.run(
                    ["git", "commit", f"--author={author}", "-m", message],
                    check=True,
                    encoding="UTF8",
                    cwd=tempdir,
                )
                return subprocess.run(
                    ["git", "format-patch", "--stdout", "HEAD^"],
                    check=True,
                    encoding="UTF8",
                    cwd=tempdir,
                    stdout=subprocess.PIPE,
                ).stdout
            finally:
                subprocess.run(
                    [
                        "git",
                        f"--git-dir={self.repo}",
                        "worktree",
                        "remove",
                        tempdir,
                        "--force",
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        f"--git-dir={self.repo}",
                        "branch",
                        "--delete",
                        "--force",
                        tempdir.name,
                    ],
                    check=True,
                )


repo = Repo()


def _get_form_field(input_, name: str):
    values = input_.get(name.encode("UTF8"), [])
    assert len(values) < 2
    return values[0].decode("UTF8") if values else None


def quick_patch_app(environ, start_response):
    path = environ["PATH_INFO"][1:]
    input_ = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"] or "0"))
    input_ = urllib.parse.parse_qs(input_)
    global repo

    posted_file = _get_form_field(input_, "file")
    file = posted_file or repo.get_file(path)

    patch = ""
    if posted_file:
        author = f"{_get_form_field(input_, 'name') or 'unknown'} <{_get_form_field(input_, 'email') or 'unknown@example.com'}>"
        message = _get_form_field(input_, "summary") or "Apply feedback"
        description = _get_form_field(input_, "description")
        if description:
            message += "\n\n"
            message += description
        patch = repo.make_patch(path, file.replace("\r\n", "\n"), author, message)

    out = f"""
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <style>
          textarea[name=file] {{
            width: 100%;
            height: 80%;
          }}

          label {{
            display: block;
          }}
        </style>
      </head>
      <body>
        <form action="{environ["PATH_INFO"]}" method="POST">
          (All fields are optional.)
          <label>Your name
            <input name="name">
          </label>
          <label>Your email address (optional, will be published)
            <input name="email" type="email">
          </label>
          <label>Summary of the change
            <input name="summary" size="50">
          </label>
          <label>Description of the change
            <textarea name="description" cols="72" rows="5"></textarea>
          </label>
          <label>Proposed change
            <textarea name="file">{html.escape(file)}</textarea>
          </label>
          <input type="submit">
        </form>
        <pre>{html.escape(patch)}</pre>
      </body>
    </html>
    """

    headers = [("Content-type", "text/html; charset=utf-8")]
    start_response("200 OK", headers)

    return [out.encode("UTF8")]


with make_server("", 8000, quick_patch_app) as httpd:
    print("http://0.0.0.0:8000")

    httpd.serve_forever()
