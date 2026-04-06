import html
import os
import pathlib
import subprocess
import tempfile
import urllib.parse

from wsgiref.simple_server import make_server


class Repo:
    def __init__(self, repo, branch):
        self.repo = repo
        self.branch = branch

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
                patch_path = tempdir / path
                assert patch_path.relative_to(tempdir)
                patch_path.write_text(patched)
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


def _get_form_field(input_: dict[bytes, list[bytes]], name: str):
    values = input_.get(name.encode("UTF8"), [])
    assert len(values) < 2
    return values[0].decode("UTF8") if values else None


def quick_patch_app(environ, start_response):
    repo = Repo(pathlib.Path(os.environ["REPO"]), os.environ["DEFAULT_BRANCH"])
    path = environ["PATH_INFO"][1:]

    content_length = environ["CONTENT_LENGTH"]

    if content_length:
        content_length = int(content_length)
        input_ = environ["wsgi.input"].read(content_length)
        input_ = urllib.parse.parse_qs(input_)

        posted_file = _get_form_field(input_, "file")
        assert posted_file

        name = _get_form_field(input_, 'name') or 'unknown'
        email = _get_form_field(input_, 'email') or 'unknown@example.com'
        author = f"{name} <{email}>"

        message = _get_form_field(input_, "summary") or "Apply feedback"

        description = _get_form_field(input_, "description")
        if description:
            message += "\n\n"
            message += description

        patch = repo.make_patch(path, posted_file.replace("\r\n", "\n"), author, message)

        headers= [("Content-Disposition", 'attachment; filename="patch.patch"')]
        start_response("200 OK", headers)

        return [patch]

    file = repo.get_file(path)

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
          <input type="submit" value="Download patch">
        </form>
      </body>
    </html>
    """

    headers = [("Content-type", "text/html; charset=utf-8")]
    start_response("200 OK", headers)

    return [out.encode("UTF8")]


if __name__ == "__main__":
    with make_server("", 8000, quick_patch_app) as httpd:
        print("http://0.0.0.0:8000")

        httpd.serve_forever()


import unittest  # noqa: E402 I like it this way.


class Test(unittest.TestCase):
    def test__make_patch_does_not_traverse(self):
        with tempfile.TemporaryDirectory() as traversed:
            traversed = pathlib.Path(traversed) / "foo"
            try:
                with tempfile.TemporaryDirectory() as repo:
                    repo = pathlib.Path(repo)
                    traversed = pathlib.Path(traversed)
                    subprocess.run(["git", "init", "--bare"], cwd=repo, check=True)
                    repo = Repo(repo, "main")
                    repo.make_patch(traversed, "foo", None, None)
            except subprocess.CalledProcessError as e:
                # Branch clean up fails
                assert e.cmd[0:1] + e.cmd[2:5] == [
                    "git",
                    "branch",
                    "--delete",
                    "--force",
                ]
            assert not traversed.exists()
