# VPS deployment

The `main` branch is deployed by `.github/workflows/deploy.yml`.

The workflow connects to the dedicated `paperdeploy` user on the VPS. It does not use a GitHub Deploy Key. Add the private half of the VPS deployment SSH key as the repository Actions secret `PAPER_VPS_SSH_KEY`.

