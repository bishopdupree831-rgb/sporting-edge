# Sporting Edge Deploy Guide

## GitHub Setup

Official GitHub docs:

- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github

Useful commands:

```bash
git status
git add .
git commit -m "Upgrade Sporting Edge dashboard UI and deployment setup"
git branch -M main
```

If the remote already exists:

```bash
git push origin main
```

If the remote does not exist:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Never commit real API keys. Only commit `.env.example`. Keep `.env` ignored.

## Render Deployment

Recommended host: Render.

Official Render docs:

- https://render.com/docs/deploy-fastapi
- https://github.com/render-examples/fastapi

Steps:

1. Go to https://render.com
2. Create an account or sign in.
3. Click `New` then `Web Service`.
4. Connect your GitHub repository.
5. Select the `sporting-edge` repo.
6. Use:

```text
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT
```

7. Add environment variables from `.env.example`.
8. Deploy.
9. Test:

```text
https://YOUR_RENDER_URL.onrender.com/health
```

10. Test dashboard:

```text
https://YOUR_RENDER_URL.onrender.com
```

## Optional Vercel Frontend

The current app is served by FastAPI, so Vercel is not required. If a separated React/Vite/Next frontend is added later:

Official Vercel docs:

- https://vercel.com/docs/git/vercel-for-github
- https://vercel.com/docs/deployments

Vercel steps:

1. Go to https://vercel.com
2. Add New Project.
3. Import the GitHub repo.
4. Set build command depending on frontend:

```text
npm run build
```

5. Set output directory:

```text
dist for Vite
.next for Next.js
build for Create React App
```

6. Add environment variable:

```text
VITE_API_BASE_URL=https://YOUR_RENDER_BACKEND_URL
```

7. Deploy.
