"""Static upload gate; uploads are never executed or extracted on the host."""
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile
import hashlib
ALLOWED={'.py','.json','.yaml','.yml','.toml','.txt','.zip'}
FORBIDDEN=('subprocess','os.system','shell=true','eval(','exec(','__import__(','socket.','requests.',"open('/etc",'open("/etc')
MAX_UPLOAD, MAX_MEMBER, MAX_MEMBERS, MAX_UNPACKED = 10_000_000, 2_000_000, 100, 10_000_000
def _findings(content: bytes) -> list[str]:
    text=content.decode('utf-8',errors='ignore').lower(); return [token for token in FORBIDDEN if token in text]
def _unsafe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts or "\\" in name
def inspect_upload(filename: str, content: bytes) -> dict:
    # basename prevents path traversal even if a later storage layer is added.
    if Path(filename).name != filename: return {'status':'REJECTED','reason':'اسم الملف غير آمن'}
    suffix=Path(filename).suffix.lower()
    if suffix not in ALLOWED:return {'status':'REJECTED','reason':'امتداد الملف غير مسموح'}
    if len(content)>MAX_UPLOAD:return {'status':'REJECTED','reason':'حجم الملف يتجاوز الحد'}
    findings=_findings(content)
    if suffix=='.zip':
        try:
            with ZipFile(BytesIO(content)) as archive:
                files=archive.infolist()
                total = sum(item.file_size for item in files)
                if len(files)>MAX_MEMBERS or total>MAX_UNPACKED:return {'status':'REJECTED','reason':'محتوى ZIP كبير جدًا'}
                for item in files:
                    if item.flag_bits&1 or _unsafe_member(item.filename) or item.is_dir():
                        if item.flag_bits&1 or _unsafe_member(item.filename): return {'status':'REJECTED','reason':'محتوى ZIP غير آمن'}
                        continue
                    # Unix symlink mode and high compression ratios are unsafe.
                    if (item.external_attr >> 16) & 0o170000 == 0o120000 or item.file_size>MAX_MEMBER or (item.compress_size and item.file_size / item.compress_size > 100): return {'status':'REJECTED','reason':'محتوى ZIP غير آمن أو كبير'}
                    findings.extend(_findings(archive.read(item)))
        except BadZipFile:return {'status':'REJECTED','reason':'ملف ZIP غير صالح'}
    return {'status':'REJECTED' if findings else 'PENDING_REVIEW','checksum':hashlib.sha256(content).hexdigest(),'findings':sorted(set(findings)),'reason':'يتطلب sandbox معزولًا وتحليلًا ساكنًا واختبارات وBacktest قبل الاعتماد'}
