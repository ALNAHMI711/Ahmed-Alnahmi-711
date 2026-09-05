from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import hashlib
ALLOWED={'.py','.json','.yaml','.yml','.toml','.txt','.zip'}
FORBIDDEN=('subprocess','os.system','shell=true','eval(','exec(','__import__(','socket.','requests.',"open('/etc",'open("/etc')
def _findings(content:bytes)->list[str]:
    text=content.decode('utf-8',errors='ignore').lower();return [token for token in FORBIDDEN if token in text]
def inspect_upload(filename:str,content:bytes)->dict:
    suffix=Path(filename).suffix.lower()
    if suffix not in ALLOWED:return {'status':'REJECTED','reason':'امتداد الملف غير مسموح'}
    if len(content)>10_000_000:return {'status':'REJECTED','reason':'حجم الملف يتجاوز الحد'}
    findings=_findings(content)
    if suffix=='.zip':
        try:
            with ZipFile(BytesIO(content)) as archive:
                files=archive.infolist()
                if len(files)>100:return {'status':'REJECTED','reason':'عدد ملفات ZIP يتجاوز الحد'}
                if any(item.flag_bits&1 for item in files):return {'status':'REJECTED','reason':'ملف ZIP مشفر ولا يمكن فحصه'}
                if any(item.file_size>2_000_000 or item.filename.startswith(('/', '../')) for item in files):return {'status':'REJECTED','reason':'محتوى ZIP غير آمن أو كبير'}
                for item in files:
                    if not item.is_dir(): findings.extend(_findings(archive.read(item)))
        except BadZipFile:return {'status':'REJECTED','reason':'ملف ZIP غير صالح'}
    return {'status':'REJECTED' if findings else 'PENDING_REVIEW','checksum':hashlib.sha256(content).hexdigest(),'findings':sorted(set(findings)),'reason':'يتطلب sandbox معزولًا وتحليلًا ساكنًا واختبارات وBacktest قبل الاعتماد'}
