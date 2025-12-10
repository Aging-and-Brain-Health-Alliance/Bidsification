import constants
import os
import re
import pandas as pd
from GluckLab.utils import subjectid_to_seqid as s2s
from multiprocessing import Pool


def fix_subjectid(subjectid):
    fixed_id = str(subjectid).upper()
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


def get_checklist() -> pd.DataFrame:
    checklist = pd.read_excel(constants.mri_checklist_path)
    with Pool() as p:
        fixed_subjectids = p.map(fix_subjectid, checklist["SUBJECT_ID"])
    checklist["correct_subjectid"] = fixed_subjectids
    checklist["BIDS_id"] = checklist["correct_subjectid"].apply(
        s2s.get_seqid
    )
    checklist["session"] = checklist["correct_subjectid"].apply(
        s2s.get_instance_number
    )
    return checklist


def check_bidsification(row, prisma_subjects, qmri_subjects):
    if pd.isnull(row["BIDS_id"]):
        return "No"
    subject = "sub-" + row["BIDS_id"]
    session = "ses-" + str(int(row["session"]))
    if subject in prisma_subjects:
        sessions = os.listdir(os.path.join(
            constants.prisma_merged_path, subject))
        if session in sessions:
            return "Yes"
    if subject in qmri_subjects:
        sessions = os.listdir(os.path.join(constants.qmri_path, subject))
        if session in sessions:
            return "Yes"
    return "No"


def main():
    checklist = get_checklist()
    subs = checklist[["BIDS_id", "session"]]
    rows = [row for _, row in subs.iterrows()]
    prisma_subjects = [d for d in os.listdir(
        constants.prisma_merged_path) if d.startswith("sub")]
    qmri_subjects = [d for d in os.listdir(
        constants.qmri_path) if d.startswith("sub")]

    check_input = [(row, prisma_subjects, qmri_subjects) for row in rows]
    with Pool() as p:
        bidsified = p.starmap(check_bidsification, check_input)
    checklist["BIDSified"] = bidsified
    checklist = checklist[[
        "SUBJECT_ID", "correct_subjectid", "BIDSified", "BIDS_id", "session"]]
    checklist.to_excel(
        os.path.join(constants.bidsified_participants_path,
                     "fixed_ids.xlsx"),
        index=False
    )


if __name__ == "__main__":
    main()
