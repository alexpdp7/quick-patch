import html
import os
import pathlib
import subprocess

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


repo = Repo()


def quick_patch_app(environ, start_response):
    path = environ["PATH_INFO"][1:]
    global repo

    file = repo.get_file(path)

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
        <form>
          <textarea>{html.escape(file)}</textarea>
        </form>
      </body>
    </html>
    """

    headers = [("Content-type", "text/html; charset=utf-8")]
    start_response("200 OK", headers)

    return [out.encode("UTF8")]


with make_server("", 8000, quick_patch_app) as httpd:
    print("http://0.0.0.0:8000")

    httpd.serve_forever()
