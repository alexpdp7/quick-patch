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

    def make_patch(self, path, patched):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = pathlib.Path(tempdir)
            subprocess.run(
                ["git", f"--git-dir={self.repo}", "worktree", "add", tempdir],
                check=True,
            )
            try:
                (tempdir / path).write_text(patched)
                return subprocess.run(
                    ["git", "diff"],
                    check=True,
                    stdout=subprocess.PIPE,
                    encoding="UTF8",
                    cwd=tempdir,
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


repo = Repo()


def quick_patch_app(environ, start_response):
    path = environ["PATH_INFO"][1:]
    input_ = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"] or "0"))
    input_ = urllib.parse.parse_qs(input_)
    global repo

    posted_files = input_.get(b"file", [])
    assert len(posted_files) < 2
    file = posted_files[0].decode("UTF8") if posted_files else repo.get_file(path)

    patch = ""
    if posted_files:
        patch = repo.make_patch(
            path, posted_files[0].decode("UTF8").replace("\r\n", "\n")
        )

    out = f"""
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <style>
          textarea {{
            width: 100%;
            height: 80%;
          }}
        </style>
      </head>
      <body>
        <form action="{environ["PATH_INFO"]}" method="POST">
          <textarea name="file">{html.escape(file)}</textarea>
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
