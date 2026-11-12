"""List and extract the archive of originals into its own folder (names decoded as cp932 when needed)."""
import hashlib, os, sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
with zipfile.ZipFile(src) as z:
    for info in z.infolist():
        name = info.filename
        if not (info.flag_bits & 0x800):
            try:
                name = info.filename.encode("cp437").decode("cp932")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        base = os.path.basename(name.rstrip("/"))
        if info.is_dir() or not base:
            print("DIR ", name)
            continue
        target = os.path.join(dst, base)          # flat: never follow paths stored in the archive
        with z.open(info) as fh, open(target, "wb") as out:
            h = hashlib.sha256()
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk); h.update(chunk)
        os.chmod(target, 0o444)                    # read-only
        print("FILE", name, info.file_size, h.hexdigest()[:16])
