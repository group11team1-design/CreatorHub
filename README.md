# CreatorHub Store — Complete Creator Edition

A Microsoft Store-inspired digital marketplace built with Python Flask, SQLite, HTML, CSS and JavaScript.

## 1. Install and run on Windows

Extract the ZIP, open the extracted folder in VS Code, then open its terminal:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the store: `http://127.0.0.1:5000`

## 2. Create your private creator login (first run only)

Open `http://127.0.0.1:5000/admin/setup`.

- Choose your creator username.
- Choose a password with at least 10 characters.
- Confirm the password and create your account.

This setup page automatically redirects to the login after the first account is created. Passwords are stored as secure password hashes, not plain text. There is no public registration page.

Next time, sign in at `http://127.0.0.1:5000/admin/login`. The creator dashboard is at `http://127.0.0.1:5000/admin`.

## 3. Publish any creation

From Creator Studio choose **New creation**:
- Enter title, category, version, description and compatibility.
- Upload the main file. Any file extension is accepted (500 MB combined request limit).
- Add a cover image and multiple screenshots (PNG, JPG, JPEG, WEBP or GIF).
- Preview selected images before publishing.

The creation appears in the public store after publishing. Visitors can browse and download, but cannot access creator routes. Creator actions require a private login and CSRF-protected forms.

## 4. Creator details shown in App Details

Set these optional Windows environment variables before starting the app:
```bat
set CREATOR_NAME=Your Display Name
set CREATOR_TAGLINE=Independent app and digital creator
set CREATOR_BIO=I build apps, extensions, games and creative tools.
set CREATOR_LOCATION=India
python app.py
```
These details appear in each product's **Additional information → Creator / Publisher** section.

## 5. Keep your content safe when upgrading

Back up and preserve:
- `creatorhub.db` — creator account and all product listings.
- `uploads/` — all uploaded files, covers and screenshots.
- `.secret_key` — keeps your local login session secret stable between restarts.

Do not delete these when replacing application code. If you delete the database, you will need to create a new creator account.

## Security and deployment notes

- Use HTTPS and set a long random `SECRET_KEY` for public deployment.
- Use a production WSGI server instead of Flask's development server.
- Add malware scanning and download moderation before allowing public uploads (only the creator can upload in this design).
- Configure persistent storage and regular backups. The default SQLite + local disk setup is suitable as a local starter project.


## Downloads page

The sidebar **Downloads** link opens `/downloads`, a dedicated download centre listing all published creations with search and direct download links. Download links increment the download counter when the file is served.
