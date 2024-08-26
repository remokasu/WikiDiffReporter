import requests
from urllib.parse import urlparse, unquote
import difflib
import json
from datetime import datetime
from jinja2 import Template
from argparse import ArgumentParser

####################################
# Get user revisions from Wikipedia
####################################


def calculate_diff(old_text, new_text):
    d = difflib.Differ()
    diff = list(d.compare(old_text.splitlines(), new_text.splitlines()))

    added = sum(len(line) - 2 for line in diff if line.startswith("+ "))
    removed = sum(len(line) - 2 for line in diff if line.startswith("- "))

    diff_text = []
    for line in diff:
        if line.startswith("+ "):
            diff_text.append("+" + line[2:])
        elif line.startswith("- "):
            diff_text.append("-" + line[2:])

    return added, removed, "\n".join(diff_text)


def extract_title_from_url(url):
    path = urlparse(url).path
    title = path.split("/")[-1]
    return unquote(title.replace("_", " "))


def get_user_revisions(page_url, username, limit=500):
    page_title = extract_title_from_url(page_url)

    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "ids|timestamp|user|comment|content",
        "rvlimit": limit,
        "rvuser": username,
        "rvslots": "main",
        "redirects": 1,
    }

    revisions = []
    while True:
        try:
            response = requests.get(url, params=params).json()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break

        if "error" in response:
            print(f"Error: {response['error']['info']}")
            break
        page = next(iter(response["query"]["pages"].values()))

        if "revisions" in page:
            revisions.extend(page["revisions"])

        if "continue" in response:
            params.update(response["continue"])
        else:
            break

    return revisions


def get_previous_revision(page_title, rev_id):
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "ids|timestamp|user|comment|content",
        "rvlimit": 1,
        "rvstartid": rev_id - 1,  # Get the revision before the specified revision ID
        "rvdir": "older",
        "rvslots": "main",
        "redirects": 1,
    }
    response = requests.get(url, params=params).json()
    page = next(iter(response["query"]["pages"].values()))

    if "revisions" in page:
        return page["revisions"][0]
    return None


def show_diff(old_text, new_text):
    diff = difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(), lineterm="", n=0
    )
    return "\n".join(
        line for line in diff if line.startswith("+") or line.startswith("-")
    )


def create_json_report(revisions, page_url, username):
    report = {
        "page_url": page_url,
        "page_title": extract_title_from_url(page_url),
        "username": username,
        "total_revisions": len(revisions),
        "revisions": [],
    }

    previous_text = ""
    for i, rev in enumerate(revisions):
        revision_data = {
            "revision_id": rev["revid"],
            "timestamp": rev["timestamp"],
            "comment": rev["comment"],
        }

        if "slots" in rev and "main" in rev["slots"]:
            current_text = rev["slots"]["main"].get("*", "")

            revision_data["content_length"] = len(current_text)

            if i == 0:
                previous_revision = get_previous_revision(
                    report["page_title"], rev["revid"]
                )
                if previous_revision:
                    previous_text = previous_revision["slots"]["main"].get("*", "")

            added, removed, diff_text = calculate_diff(previous_text, current_text)
            revision_data["changes"] = {
                "added": added,
                "removed": removed,
                "diff": diff_text,
            }

            previous_text = current_text
        else:
            revision_data["warning"] = "Expected keys not found in revision"

        report["revisions"].append(revision_data)

    return report


####################################
# Convert JSON report to HTML
####################################


def json_to_html(json_filename, title, capture_datetime):
    with open(json_filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not title:
        title = f"Wikipedia Edit Report for {data['username']} on {data['page_title']}"

    template = Template(
        """
<html>
<head>
<title>{{ title }}</title>
<style>
body { font-family: Arial, sans-serif; }
.revision { margin-bottom: 20px; border-bottom: 1px solid #ccc; }
.diff { white-space: pre-wrap; font-family: monospace; }
.addition { color: green; }
.deletion { color: red; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<p><strong>Page:</strong> <a href="{{ data.page_url }}">{{ data.page_title }}</a></p>
<p><strong>User:</strong> {{ data.username }}</p>
<p><strong>Total Revisions:</strong> {{ data.total_revisions }}</p>
<p><strong>Captured On:</strong> {{ capture_datetime }}</p>

{% for rev in data.revisions %}
<div class="revision">
<h2>Revision {{ rev.revision_id }}</h2>
<p><strong>Timestamp:</strong> {{ rev.timestamp }}</p>
<p><strong>Comment:</strong> {{ rev.comment }}</p>
{% if rev.content_length is defined %}
<p><strong>Content Length:</strong> {{ rev.content_length }} characters</p>
{% endif %}
{% if rev.changes is defined %}
<h3>Changes:</h3>
<p><strong>Added:</strong> {{ rev.changes.added }} characters</p>
<p><strong>Removed:</strong> {{ rev.changes.removed }} characters</p>
{% if rev.changes.diff %}
<pre class="diff">{% for line in rev.changes.diff.split('\n') %}{% if line.startswith('+') %}<span class="addition">{{ line }}</span>{% elif line.startswith('-') %}<span class="deletion">{{ line }}</span>{% else %}{{ line }}{% endif %}
{% endfor %}</pre>
{% else %}
<p>No visible changes in the content.</p>
{% endif %}
{% endif %}
{% if rev.warning is defined %}
<p><strong>Warning:</strong> {{ rev.warning }}</p>
{% endif %}
</div>
{% endfor %}
</body>
</html>
"""
    )

    html_content = template.render(data=data, title=title, capture_datetime=capture_datetime)

    html_filename = json_filename.replace(".json", ".html")
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML report saved as {html_filename}")


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("-url", type=str, default="", help="Wikipedia page URL")
    parser.add_argument("-user", type=str, default="", help="Wikipedia username")
    args = parser.parse_args()

    page_url = args.url
    username = args.user

    if page_url == "" or username == "":
        print("Please provide the Wikipedia page URL and username")
        print("Example: python diff.py -url [URL] -username [USERNAME]")
        exit()

    revisions = get_user_revisions(page_url, username)
    revisions.sort(key=lambda x: x["timestamp"])

    json_report = create_json_report(revisions, page_url, username)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"wikipedia_edit_report_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)

    print(f"Report saved as {filename}")

    title = f"Wikipedia Edit Report for {username} on {extract_title_from_url(page_url)}"
    json_to_html(filename, title, timestamp)

    print("Conversion to HTML complete")
