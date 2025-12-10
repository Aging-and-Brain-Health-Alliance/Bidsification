import pandas as pd
from GluckLab.utils import subjectid_to_seqid as s2s
import os


def get_triggers():
    log_files = [
        os.path.join("data", file) for file in os.listdir("data") if (file.endswith(".log") and "test" not in file.lower())
    ]
    csv_files = [
        os.path.join("data", file) for file in os.listdir("data") if (file.endswith(".csv") and "test" not in file.lower())
    ]
    triggers = []
    for log_file in log_files:
        subject = os.path.basename(log_file)[12:-4]
        csv = None
        for csv_file in csv_files:
            if subject in csv_file:
                csv = csv_file
        if csv is None:
            continue
        with open(log_file, "r") as log:
            for line in log:
                if "Keypress: t" in line:
                    time = float(line[:8])
                    triggers.append({
                        "subject": subject,
                        "seqid": s2s.get_seqid(subject),
                        "session": f"{s2s.get_instance_number(subject):02}",
                        "trigger": time,
                        "csv": csv,
                        "log": log_file
                    })
                    break
    triggers_df = pd.DataFrame(triggers)
    return triggers_df


def calculate_timings(df: pd.DataFrame) -> pd.DataFrame:
    timings = []
    csv = pd.read_csv(df["csv"])
    cols_needed = [
        "subject_response.started",
        "current_phase",
        "subject_response.rt",
        "subject_response.corr",
        "subject_response.keys",
        "Left_Stim",
    ]
    if csv.empty:
        return pd.DataFrame([{"error": "empty csv file"}])
    if any([col not in csv.columns for col in cols_needed]):
        return pd.DataFrame([{"error": "Necessary columns not present"}])

    print(df["csv"])
    csv = csv[csv["Left_Stim"].notna()]
    for index, row in csv.iterrows():
        if pd.notna(row["instructions1.started"]):
            timing_row = {
                "onset": row["instructions1.started"] - df["trigger"],
                "duration": 15,
                "event": "instructions",
                "response_time": pd.NA,
                "correctness": pd.NA,
                "response": pd.NA,
                "stimulus": "initial_instructions",
                "cond": pd.NA
            }
            timings.append(timing_row)
        if pd.notna(row["post_practice_text.started"]):
            timing_row = {
                "onset": row["post_practice_text.started"] - df["trigger"],
                "duration": 10,
                "event": "instructions",
                "response_time": pd.NA,
                "correctness": pd.NA,
                "response": pd.NA,
                "stimulus": "post_practice_instructions",
                "cond": pd.NA
            }
            timings.append(timing_row)
        if pd.notna(row["long_rest_screen.started"]):
            timing_row = {
                "onset": row["long_rest_screen.started"] - df["trigger"],
                "duration": 15,
                "event": "rest",
                "response_time": pd.NA,
                "correctness": pd.NA,
                "response": pd.NA,
                "stimulus": "long_rest_screen",
                "cond": pd.NA
            }
            timings.append(timing_row)

        timing_row = {
            "onset": row["subject_response.started"] - df["trigger"],
            "duration": 6,
            "event": row["current_phase"],
            "response_time": row["subject_response.rt"],
            "correctness": "correct" if row["subject_response.corr"] == 1 else "incorrect",
            "response": "left" if row["subject_response.keys"] == "b" else "right",
            "stimulus": row["Relevant_Feature"] if pd.notna(row["Relevant_Feature"]) else "practice_pair",
            "cond": row["Left_Stim"][0] if row["Left_Stim"][0].isdigit() else "practice"
        }
        timings.append(timing_row)
    timings = pd.DataFrame(timings)
    return timings


def main():
    triggers = get_triggers()
    for index, row in triggers.iterrows():
        timing = calculate_timings(row)
        timing_filename = f"sub-{row["seqid"]
                                 }_ses-{row["session"]}_task-ChooseFmri_events.tsv"
        timing.to_csv(os.path.join("timings", timing_filename),
                      sep="\t", index=False)


if __name__ == "__main__":
    main()
