# CIA Converter Cloud Version

GitHub account: chromaticinnovision

## Features
- Login page
- CIA logo branding
- NEF / RAW / CR2 / ARW / DNG → JPG
- JPG / PNG / WEBP conversion
- Image → PDF
- Download as ZIP
- Temporary files auto deleted after conversion
- Designed for Render deployment

## Default Login
Username: `cia`
Password: `Maybe1651!`

For production, set login inside Render Environment Variables.

## Upload to GitHub
1. Login GitHub
2. Create new repository: `cia-converter-cloud`
3. Upload all files from this folder into the repository.

## Deploy on Render
1. Login Render
2. New → Web Service
3. Connect GitHub repository: `chromaticinnovision / cia-converter-cloud`
4. Settings:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Add Environment Variables:
   - `SECRET_KEY` = make-a-long-random-secret-here
   - `LOGIN_USERNAME` = cia
   - `LOGIN_PASSWORD` = Maybe1651!
   - `MAX_CONTENT_LENGTH_MB` = 300
6. Deploy.

Render will give you a URL like `https://cia-converter-cloud.onrender.com`. Test this first.

## Connect converter.chromatic.my
After Render works:
1. Render app → Settings → Custom Domains
2. Add `converter.chromatic.my`
3. Render will show DNS target.
4. Login Exabytes → DNS Management for `chromatic.my`
5. Add CNAME:
   - Type: CNAME
   - Name: converter
   - Target: Render DNS target
   - TTL: Default

Then open `https://converter.chromatic.my`.

## Important
Do not make the GitHub repository public if you don't want others to see the code structure.
Do not store customer files permanently. This app deletes temporary files after conversion.
