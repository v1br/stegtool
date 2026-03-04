import numpy as np
import csv
import os


def print_report(r):

    print("\n================ IMAGE ANALYSIS REPORT ================")

    print("File                :", r["file"])
    print("Resolution          :", r["width"], "x", r["height"])

    print("\n--- Detection Result ---")

    print("Prediction          :", r["label"])
    print("Average probability :", round(r["probability"] * 100, 2), "%")

    # Ensemble information (if available)
    if "consensus" in r:
        total_models = len(r.get("model_probabilities", {}))
        print("Model consensus     :", r["consensus"], "/", total_models)

    if "estimated_payload" in r:
        print("Estimated payload   : ~", r["estimated_payload"], "bpp")

    # Individual model outputs
    if "model_probabilities" in r:

        print("\n--- Model Responses ---")

        for bpp, prob in sorted(r["model_probabilities"].items()):
            print(f"{bpp} bpp detector      :", round(prob, 4))

    print("\n--- Statistical Indicators ---")

    print("LSB Entropy         :", round(r["entropy"], 4))

    glcm = r["glcm"]

    print("GLCM Contrast       :", round(glcm[0], 4))
    print("GLCM Correlation    :", round(glcm[1], 4))
    print("GLCM Energy         :", round(glcm[2], 4))
    print("GLCM Homogeneity    :", round(glcm[3], 4))

    spam = r["spam"]

    print("\n--- SPAM Residual Stats ---")

    print("Mean                :", round(float(np.mean(spam)), 6))
    print("Std Dev             :", round(float(np.std(spam)), 6))

    print("=======================================================")


def print_summary(results):

    total = len(results)

    stego = sum(1 for r in results if r["label"] == "STEGO")
    suspicious = sum(1 for r in results if r["label"] == "SUSPICIOUS")
    clean = sum(1 for r in results if r["label"] == "COVER")

    investigation = stego + suspicious

    print("\n================ FORENSIC SUMMARY =================")

    print("Images scanned        :", total)
    print("Stego detected        :", stego)
    print("Suspicious images     :", suspicious)
    print("Clean images          :", clean)

    print("\nInvestigation needed  :", investigation)

    if investigation > 0:

        print("\nHigh priority files:")

        for r in results:
            if r["label"] in ("STEGO", "SUSPICIOUS"):
                print(" -", os.path.basename(r["file"]))

    print("===================================================\n")


def export_results(results):

    os.makedirs("reports", exist_ok=True)

    all_path = "reports/analysis_results.csv"
    stego_path = "reports/stego_detected.csv"
    suspicious_path = "reports/suspicious_images.csv"

    fields = [
        "file",
        "prediction",
        "probability",
        "entropy",
        "glcm_contrast",
        "glcm_correlation",
        "glcm_energy",
        "glcm_homogeneity"
    ]

    with open(all_path, "w", newline="") as f_all, \
         open(stego_path, "w", newline="") as f_stego, \
         open(suspicious_path, "w", newline="") as f_suspicious:

        writer_all = csv.writer(f_all)
        writer_stego = csv.writer(f_stego)
        writer_suspicious = csv.writer(f_suspicious)

        writer_all.writerow(fields)
        writer_stego.writerow(fields)
        writer_suspicious.writerow(fields)

        for r in results:

            row = [
                r["file"],
                r["label"],
                round(r["probability"], 4),
                round(r["entropy"], 4),
                round(r["glcm"][0], 4),
                round(r["glcm"][1], 4),
                round(r["glcm"][2], 4),
                round(r["glcm"][3], 4),
            ]

            writer_all.writerow(row)

            if r["label"] == "STEGO":
                writer_stego.writerow(row)

            if r["label"] == "SUSPICIOUS":
                writer_suspicious.writerow(row)

    print("Reports saved to 'reports/' directory")


def print_dataset_comparison(tool, result):

    baseline = tool.baseline

    entropy_dev = baseline.z_score(result["entropy"], "entropy")

    print("\n--- Dataset Comparison ---")
    print("Entropy deviation :", round(entropy_dev, 2), "sigma")


def print_feature_explanation(tool):

    if tool.feature_importance is None:
        return

    importance = tool.feature_importance

    top = np.argsort(importance)[::-1][:5]

    print("\n--- Model Explanation ---")
    print("Top influential feature indices:")

    for i in top:
        print("Feature", i, "importance:", round(float(importance[i]), 6))