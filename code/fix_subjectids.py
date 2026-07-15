import os
import sys
import re
import zipfile
from multiprocessing import Pool


def extract_zipfile(src, dest):
    try:
        with zipfile.ZipFile(src) as zip_ref:
            zip_ref.extractall(dest)
    except Exception as error:
        print(f"{src}:\n{error}")


def fix_id(subjectid):
    fixed_id = str(subjectid).upper()
    fixed_id = fixed_id.replace("_DICOM", "")
    fixed_id = fixed_id.replace("_O", "")
    fixed_id = fixed_id.replace("_Q", "")
    fixed_id = fixed_id.replace("QMRI_", "")
    if re.match("EX[0-9]{3}[_/]{1}", fixed_id):
        fixed_id = fixed_id[6:]
    if re.search("AA(([0-9]?R)?[0-9]{3})(L)?", fixed_id):
        match = re.search("AA(([0-9]?R)?[0-9]{3})(L)?", fixed_id)
        fixed_id = f"AA_{match.group(1)}"
        if match.group(3):
            fixed_id += f"_{match.group(3)}"
    if re.match("AA_[0-9]{3}", fixed_id):
        fixed_id = fixed_id.replace("AA_", "AA")
    if "C0V" in fixed_id:
        fixed_id = fixed_id.replace("C0V", "COV")
    if "COVR" in fixed_id:
        fixed_id = fixed_id.replace("COVR", "COV_R")
    return fixed_id


def main():
    dir_to_fix = sys.argv[1]
    dest_dir = sys.argv[2]
    dirs = []
    zipfiles = []
    fixed = {}
    for filename in os.listdir(dir_to_fix):
        filepath = os.path.join(dir_to_fix, filename)
        if filepath.endswith("zip"):
            id = filename.replace(".zip", "")
            zipfiles.append(
                (filepath, os.path.join(dest_dir, fix_id(id)))
            )
        elif not (filename.startswith("@") or filename.startswith(".")):
            fixed[filepath] = fix_id(filename)
            dirs.append(filepath)

    with Pool() as p:
        p.starmap(extract_zipfile, zipfiles)
        p.starmap(os.rename, fixed.items())


if __name__ == "__main__":
    main()
