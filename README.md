# File Storage

## File management upgrade

For an existing database, run `schema_upgrade_management.sql` and then `schema_upgrade_google_auth.sql`. The latter removes legacy authentication fields and adds Google identity fields without changing stored file locations.

A personal file storage app built with Flask, MySQL, Jinja2, vanilla JavaScript, Google Identity Services, and local filesystem storage.

## Features

- Google Identity Services sign-in with server-side ID-token validation
- Local Google-subject records and secure Flask sessions
- CSRF protection for all POST forms
- Drag-and-drop uploads and file picker
- 50 MB server-enforced file limit by default
- Private per-user file folders with ownership checks
- In-browser viewing for supported file types, downloads, Trash-based deletion, and file metadata
- Responsive HTML, CSS, and JavaScript UI

## Requirements

- Python 3.9 or newer
- MySQL Server 8.0 or compatible server
- A MySQL account with permission to use `file_storage`
- A Google OAuth web client ID configured as `GOOGLE_CLIENT_ID`

## Database setup

Start MySQL, then run the supplied schema. In Windows PowerShell:

```powershell
mysql -u root -p < schema.sql
```

It creates the `file_storage` database and the `users` and `files` tables. If your account cannot create a database, ask an administrator to run `schema.sql` and grant access.

## Python setup

Create and activate a virtual environment.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

Linux or macOS:

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Install application dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env`, then configure the MySQL credentials for your machine.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```sh
cp .env.example .env
```

Example settings:

```ini
SECRET_KEY=replace-with-a-long-random-secret
DB_HOST=localhost
DB_PORT=3306
DB_NAME=file_storage
DB_USER=root
DB_PASSWORD=your-mysql-password
UPLOAD_FOLDER=uploads
MAX_FILE_SIZE_MB=50
SESSION_COOKIE_SECURE=false
FLASK_DEBUG=false
PRIVACY_CONTACT_EMAIL=privacy@example.org
```

Generate a long, unpredictable `SECRET_KEY`. Keep `.env` private; it is ignored by Git. Set `SESSION_COOKIE_SECURE=true` only when serving the app through HTTPS; leave it false for normal local HTTP use. Set `PRIVACY_CONTACT_EMAIL` to the church or Library administrator address that should appear in the Privacy Notice; when omitted, the page directs users to the JFCM Pila church office.

## Run

```powershell
python app.py
```

Visit `http://127.0.0.1:5000`.

## Preview migration for an existing database

New installations receive the `share_token` column from `schema.sql`. If you already created the database before adding previews, run this migration once:

```powershell
mysql -u root -p file_storage < schema_upgrade_preview.sql
```

The preview page supports JPEG, PNG, GIF, WEBP, PDF, TXT, MP4, WEBM, MP3, WAV, and OGG. Copy Link creates a random-token URL, but it remains protected: the signed-in owner must still match the file owner. This design permits an explicit public-sharing option to be added later without exposing storage paths.

PowerPoint previews are rendered server-side through LibreOffice and PDF into high-resolution slide images. The dashboard displays those finished slide pixels instead of rebuilding the deck in HTML or JavaScript, preserving PowerPoint layout, layering, gradients, transparency, cropping, and slide dimensions as closely as the server's installed fonts allow. The original `.ppt`, `.pptx`, `.pps`, `.ppsx`, or `.odp` upload is never modified and remains the download source.

Install LibreOffice on the application host and make `libreoffice` or `soffice` available on `PATH`, or set `LIBREOFFICE_BINARY` to its executable. At startup the service logs the resolved executable path, or a clear error if no executable is available. `PRESENTATION_PREVIEW_DPI` controls the cached PNG quality (default `240`, clamped to `144`–`360`). Install on Linux, for example, with:

```sh
apt-get install libreoffice
```

For the closest font match, install the fonts used by uploaded presentations on the server. The Docker runtime includes open metric-compatible substitutes for common Microsoft fonts and broad Noto coverage. Organization-owned `.ttf` or `.otf` files may be placed in `fonts/` before building, subject to their licenses. Each PPTX is inspected for declared fonts, and the server logs the exact fontconfig match or substitution used. Legacy PPT files are converted to a temporary PPTX only for font inspection; the actual preview still follows the original PPT -> PDF -> PNG path. Rendered previews are cached under `uploads/.presentation-previews`; these derivative files do not replace or alter uploads.

For decks that require Microsoft PowerPoint's exact renderer, export either a PDF or one PNG per slide from PowerPoint and place it in the persistent `POWERPOINT_PRE_RENDERED_FOLDER` (defaults to `uploads/.powerpoint-prerendered`) using one of these layouts:

```text
<root>/<user_id>/<file_id>.pdf
<root>/<user_id>/<file_id>/slides.pdf
<root>/<user_id>/<file_id>/slide-1.png
<root>/<user_id>/<file_id>/slide-2.png
```

When present, this export is used as the fidelity fallback. PowerPoint-exported PNG files are copied byte-for-byte; PowerPoint-exported PDFs are rasterized page-for-page through PyMuPDF. The fallback timestamp is included in the preview cache key, so replacing an export refreshes the preview automatically.

LibreOffice's PDF export is static: it flattens each slide to its final appearance and cannot preserve PowerPoint click triggers, entrance-animation motion, easing, or timing. The service inspects PPTX timing XML and logs detected on-click sequences, but it does not rebuild animated shapes in HTML or canvas. To preserve the exact visual state and order of click reveals, capture/export each state with Microsoft PowerPoint and use zero-based step filenames:

```text
<root>/<user_id>/<file_id>/slide-1-step-0.png
<root>/<user_id>/<file_id>/slide-1-step-1.png
<root>/<user_id>/<file_id>/slide-1-step-2.png
<root>/<user_id>/<file_id>/slide-2-step-0.png
```

`step-0` is the initial state and each following image is the state after one click. Every slide must have `step-0`, and step numbers must be contiguous. The viewer advances and reverses these states before changing slides in both inline and fullscreen navigation. These images preserve PowerPoint-rendered pixels and click order; they cannot reproduce the transition motion between captured states. If no step images exist, the existing LibreOffice -> PDF -> PNG static preview remains unchanged.

Railway is configured through `railway.json` to build the root `Dockerfile` instead of relying on Railpack package propagation. The single-stage runtime image installs LibreOffice as an APT system package, verifies `libreoffice --headless --version` while building, and sets `LIBREOFFICE_BINARY=/usr/bin/libreoffice`. Startup logs show the results of resolving both `libreoffice` and `soffice` from `PATH`. Railway environment variables can still override `LIBREOFFICE_BINARY` in the service settings. The `nixpacks.toml` remains as a fallback for platforms that still use Nixpacks.

## Event sharing migration for an existing database

If Events existed before Event sharing was added, run this repeatable migration before deploying the Event sharing code. In phpMyAdmin, select `file_storage`, open the **SQL** tab, paste the migration file's contents, and click **Go**. The script does not require `DELIMITER` support.

```powershell
mysql -u root -p file_storage < schema_upgrade_event_sharing.sql
```

It adds the Event link fields (`share_token`, `share_permission`, and `is_share_link_enabled`), the unique token index, and the Event user-share table when they are missing. Existing Events retain a `NULL` token and disabled link by default; a token is created only when an owner enables that Event's share link. The migration does not modify file or folder sharing tables or data.

## Upload storage and limits

Files are stored in `uploads/<user_id>/`; this directory is not publicly served. The database keeps both the sanitized original display name and a UUID-based server filename, so duplicate uploads are safe and original filenames never become filesystem paths.

`MAX_FILE_SIZE_MB` defaults to 50. Flask rejects oversized requests using `MAX_CONTENT_LENGTH`, and the upload route also checks the size on the server. Browser-side checks only improve feedback. The dashboard calculates total used storage from metadata; a total quota can be added later.

## Security notes

- Google ID tokens are verified server-side for signature, issuer, expiration, and the configured client ID before a session is created.
- Session cookies are HTTP-only and SameSite Lax.
- SQL always uses mysql-connector parameter placeholders.
- Every file query for download or deletion includes the logged-in user id.
- Deletions are POST-only, CSRF-protected, ownership-checked, and require explicit confirmation in the interface.
- Filenames are sanitized and stored using UUID-based names.
- When metadata insertion fails, the saved physical file is removed where possible.
- Do not use `FLASK_DEBUG=true` on a public server.

## Project layout

- `app.py`: Flask routes and application setup
- `schema.sql`: MySQL database and table setup
- `.env.example`: configuration template
- `requirements.txt`: Python dependencies
- `uploads/`: private server-side uploads
- `templates/`: Jinja2 templates
- `static/css/style.css`: responsive styles
- `static/js/app.js`: client-side upload and modal behavior
