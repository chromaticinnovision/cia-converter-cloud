
import os, io, time, zipfile, tempfile, shutil
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from PIL import Image
try:
    import rawpy
except Exception as e:
    rawpy = None
    RAWPY_IMPORT_ERROR = str(e)
APP_ROOT = Path(__file__).parent
UPLOAD_ROOT = APP_ROOT / "uploads"
UPLOAD_ROOT.mkdir(exist_ok=True)
RAW_EXTENSIONS = {".nef", ".raw", ".cr2", ".arw", ".dng"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXTENSIONS = RAW_EXTENSIONS | IMAGE_EXTENSIONS
MAX_CONTENT_LENGTH_MB = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "300"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH_MB * 1024 * 1024
LOGIN_USERNAME = os.environ.get("LOGIN_USERNAME", "cia")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "Maybe1651!")
def cleanup_old_uploads(max_age_seconds=1800):
    now=time.time()
    for item in UPLOAD_ROOT.iterdir():
        try:
            if item.is_dir() and now-item.stat().st_mtime > max_age_seconds:
                shutil.rmtree(item, ignore_errors=True)
        except Exception: pass
def allowed_file(filename): return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'): return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper
@app.route('/')
def home(): return redirect(url_for('converter' if session.get('logged_in') else 'login'))
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if request.form.get('username','').strip()==LOGIN_USERNAME and request.form.get('password','')==LOGIN_PASSWORD:
            session['logged_in']=True; return redirect(url_for('converter'))
        flash('Username 或 password 不正确。')
    return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/converter')
@login_required
def converter():
    return render_template('converter.html', rawpy_ready=rawpy is not None, rawpy_error=None if rawpy is not None else RAWPY_IMPORT_ERROR, max_upload=f'{MAX_CONTENT_LENGTH_MB}MB')
@app.route('/api/status')
@login_required
def status():
    return jsonify({'app':'CIA Converter Cloud','status':'running','rawpy_ready': rawpy is not None, 'rawpy_error': None if rawpy is not None else RAWPY_IMPORT_ERROR, 'max_upload_mb': MAX_CONTENT_LENGTH_MB})
@app.route('/convert', methods=['POST'])
@login_required
def convert():
    cleanup_old_uploads()
    if 'files' not in request.files:
        flash('请先选择文件。'); return redirect(url_for('converter'))
    files = request.files.getlist('files')
    convert_to = request.form.get('convert_to','raw-to-jpg')
    valid_files = [f for f in files if f and f.filename and allowed_file(f.filename)]
    if not valid_files:
        flash('没有可转换的文件。支持 NEF / RAW / CR2 / ARW / DNG / JPG / PNG / WEBP。'); return redirect(url_for('converter'))
    job_dir = Path(tempfile.mkdtemp(prefix='cia_', dir=str(UPLOAD_ROOT)))
    try:
        zip_buffer=io.BytesIO(); converted_count=0; pdf_images=[]
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as z:
            for upload in valid_files:
                filename=Path(upload.filename).name; suffix=Path(filename).suffix.lower(); input_path=job_dir/filename; upload.save(input_path)
                try:
                    if convert_to=='raw-to-jpg':
                        if suffix not in RAW_EXTENSIONS: continue
                        if rawpy is None:
                            z.writestr(Path(filename).stem+'_ERROR.txt', f'rawpy is not ready: {RAWPY_IMPORT_ERROR}'); continue
                        with rawpy.imread(str(input_path)) as raw:
                            rgb=raw.postprocess(use_camera_wb=True,no_auto_bright=False,output_bps=8,bright=1.0)
                        img=Image.fromarray(rgb); out=io.BytesIO(); img.save(out, format='JPEG', quality=100, subsampling=0, optimize=False)
                        z.writestr(Path(filename).stem+'.jpg', out.getvalue()); converted_count += 1
                    elif convert_to in {'jpg','png','webp'}:
                        if suffix not in IMAGE_EXTENSIONS: continue
                        with Image.open(input_path) as img:
                            out=io.BytesIO()
                            if convert_to=='jpg':
                                output_name=Path(filename).stem+'.jpg'; img.convert('RGB').save(out, format='JPEG', quality=100, subsampling=0, optimize=False)
                            elif convert_to=='png':
                                output_name=Path(filename).stem+'.png'; img.save(out, format='PNG', optimize=False)
                            else:
                                output_name=Path(filename).stem+'.webp'; img.save(out, format='WEBP', quality=100, lossless=True, method=6)
                            z.writestr(output_name, out.getvalue()); converted_count += 1
                    elif convert_to=='pdf':
                        if suffix not in IMAGE_EXTENSIONS: continue
                        with Image.open(input_path) as img:
                            pdf_images.append(img.convert('RGB').copy()); converted_count += 1
                except Exception as e:
                    z.writestr(Path(filename).stem+'_ERROR.txt', f'Failed to convert {filename}: {str(e)}')
            if convert_to=='pdf' and pdf_images:
                pdf_buffer=io.BytesIO(); pdf_images[0].save(pdf_buffer, format='PDF', save_all=True, append_images=pdf_images[1:], resolution=300.0, quality=100)
                z.writestr('cia-converted-images.pdf', pdf_buffer.getvalue())
            if converted_count==0:
                z.writestr('NO_FILE_CONVERTED.txt','No file was converted. Please check selected format and file type.')
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='cia-converted-files.zip')
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
@app.errorhandler(413)
def too_large(e):
    flash(f'文件太大。当前最大上传限制是 {MAX_CONTENT_LENGTH_MB}MB。'); return redirect(url_for('converter'))
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT','8000')), debug=True)
