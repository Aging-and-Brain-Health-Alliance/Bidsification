import subprocess
import os
import shutil
import sys
import json
from multiprocessing import Pool
from GluckLab.utils import subjectid_to_seqid as s2s

def get_subjectids(dicom_data_path: str):
    return os.listdir(dicom_data_path)

def get_seqids_and_sessions(subjectids: list[str]):
    seqids = []
    sessions = []
    for subjectid in subjectids:
        seqids.append(s2s.get_seqid(subjectid))
        sessions.append(s2s.get_instance_number(subjectid))
    return seqids, sessions

def clean_ids_and_sessions(subjectids, seqids, sessions):
    clean_subjectids = []
    clean_seqids = []
    clean_sessions = []
    for subjectid, seqid, session in zip(subjectids, seqids, sessions):
        if seqid != None:
            clean_subjectids.append(subjectid)
            clean_seqids.append(seqid)
            clean_sessions.append(session)
    return clean_subjectids, clean_seqids, clean_sessions

def generate_scaffolding(dataset_location: str, dataset_name: str):
    subprocess.run(["dcm2bids_scaffold", "-o", os.path.join(dataset_location, dataset_name)])

def copy_data_to_dataset_location(dicom_data_path: str, dataset_loaction: str, dataset_name: str, parallel_processes: int):
    destination = os.path.join(dataset_loaction, dataset_name, "sourcedata")
    source_dest_pairs = []

    for dicom_dir in os.listdir(dicom_data_path):
        dicom_dir_path =  os.path.join(dicom_data_path, dicom_dir)
        dest_path = os.path.join(destination, dicom_dir)
        source_dest_pairs.append((dicom_dir_path, dest_path))
    
    with Pool(parallel_processes) as p:
        p.starmap(shutil.copytree, source_dest_pairs)

def run_dcm2bids(dataset_location: str, dataset_name: str, subjectids: list[str], seqids: list[str], sessions: list[int], dcm2bids_config_file_path: str, parallel_processes: int):
    dcm2bids_commands = []
    sourcedata_path = os.path.join(dataset_location, dataset_name, "sourcedata")
    for index in range(len(subjectids)):
        dicom_dir = os.path.join(sourcedata_path, subjectids[index])
        command = ["dcm2bids", 
                   "-d", dicom_dir, 
                   "-p", seqids[index], 
                   "-s", str(sessions[index]), 
                   "-c", dcm2bids_config_file_path,
                   "-o", os.path.join(dataset_location, dataset_name),
                   "--auto_extract_entities"
                   ]
        dcm2bids_commands.append(command)
    with Pool(parallel_processes) as p:
        p.map(subprocess.run, dcm2bids_commands)

def move_aslm0(dataset_location: str, dataset_name: str, parallel_processes: int):
    dataset_path = os.path.join(dataset_location, dataset_name)
    subjects = [dir for dir in os.listdir(dataset_path) if dir.startswith("sub-")]
    subject_source_paths = []
    derivatives_paths = []               
    aslm0_dest_paths = []
    for subject in subjects:
        sessions = [session for session in os.listdir(os.path.join(dataset_path, subject)) if session.startswith("ses-")]
        for session in sessions:
            derivatives_path = os.path.join(dataset_path, subject, session, "derivatives")
            aslm0_perf_path = os.path.join(derivatives_path, "asl-m0", "perf")
            if os.path.isdir(aslm0_perf_path):
                subject_source_paths.append(aslm0_perf_path)
                aslm0_dest_paths.append(os.path.join(dataset_path, "derivatives", "asl-m0", subject, session, "perf"))
                derivatives_paths.append(derivatives_path)

    source_dest_pairs = [(source, dest) for source, dest in zip(subject_source_paths, aslm0_dest_paths)]

    with Pool(parallel_processes) as p:
        p.map(os.makedirs, aslm0_dest_paths)
        p.starmap(shutil.move, source_dest_pairs)
        p.map(os.removedirs, [os.path.join(directory_path.split("/")[-1]) for directory_path in derivatives_paths])
        p.map(os.removedirs, derivatives_paths)

def main():

    dicom_data_path = None
    dataset_location = None
    dataset_name = None
    dcm2bids_config_file_path = None
    PARALLEL_PROCESSES = 1
    min_parallel_processes  = False
    if len(sys.argv) == 2:
        config = None
        try:
            with open(sys.argv[1], "r") as config_file:
                config = json.load(config_file)
        except Exception as e:
            print(f"Invalid Configuration File. Error:\n{e}")
        dicom_data_path = config["DICOM_DATA_PATH"]
        dataset_location = config["DATASET_LOCATION"]
        dataset_name = config["DATASET_NAME"]
        dcm2bids_config_file_path = config["DCM2BIDS_CONFIG_FILE_PATH"]
        if config["PARALLEL_PROCESSES"].lower() == "min":
            min_parallel_processes = True
        elif config["PARALLEL_PROCESSES"].isnumeric():
            PARALLEL_PROCESSES = int(config["PARALLEL_PROCESSES"])
        else:
            print("Error: PARALLEL_PROCESSES must be either 'min' or an integer")
            exit(-1)
    else:
        dicom_data_path = input("Enter the path to the DICOM data: ")
        dataset_location = input("Enter the path where you want the bidsified dataset to be created: ")
        dataset_name = input("Enter the name for the bidsifed dataset: ")
        dcm2bids_config_file_path = input("Enter the path to the dcm2bids configuration file: ")

    print(f"Reading subjects from {dataset_location}...")
    subjectids = get_subjectids(dicom_data_path)
    number_of_source_dirs = len(subjectids)
    print(f"Found {number_of_source_dirs} subjects.")

    if min_parallel_processes:
        print("Using min parallel processes")
        PARALLEL_PROCESSES = min(os.cpu_count(), len(subjectids))
    else:
        print(f"Using {PARALLEL_PROCESSES} parallel processes")

    print("Generating scaffolding...")
    generate_scaffolding(dataset_location, dataset_name)
    print("Scaffolding generated.")

    print("Copying source data to dataset location...")
    copy_data_to_dataset_location(dicom_data_path, dataset_location, dataset_name, PARALLEL_PROCESSES)
    print("Copying complete.")

    print("Translating SubjectIDs to SeqIDs and Sessions")
    seqids, sessions = get_seqids_and_sessions(subjectids)
    subjectids, seqids, sessions = clean_ids_and_sessions(subjectids, seqids, sessions)
    print(f"Translation complete. Successfully translated {len(seqids)}/{number_of_source_dirs} SubjectIDs")

    print("Running dcm2bids...")
    run_dcm2bids(dataset_location, dataset_name, subjectids, seqids, sessions, dcm2bids_config_file_path, PARALLEL_PROCESSES)
    print("dcm2bids complete")

    print("Moving asl-m0 derivatives...")
    move_aslm0(dataset_location, dataset_name, PARALLEL_PROCESSES)
    print("Asl-m0 move complete")

    print("Done.")


if __name__ == "__main__":
    main()