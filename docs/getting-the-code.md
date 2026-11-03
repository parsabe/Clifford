# Downloading the source

The project repository is https://github.com/parsabe/Clifford, on the `master` branch.
On GitHub, choose **Code → Download ZIP**, then extract the downloaded archive.
Alternatively:

```sh
git clone https://github.com/parsabe/Clifford.git
cd Clifford
```

Start with README.md for Ubuntu installation, local Gemma setup, hands-free voice, and server/client
configuration. The source lives in `clifford/`; tests, migrations, scripts and deployment examples
are included in their respective directories.

The repository excludes private `.env` files, authentication tokens, databases, downloaded models,
virtual environments and the uploaded prompt. Run `scripts/init_local.py` to generate your own private
backend configuration, and follow the README to download Gemma and the offline speech model.
No paid model-provider API key is required.

A cloud environment snapshot and a GitHub commit are separate: future edits still need to be
committed and pushed to appear in a GitHub download. Never force-push over someone else's changes.
