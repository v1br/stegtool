import argparse
from src.detector import SteganalysisTool
from src.analysis.reporting import print_report, print_summary, export_results
from src.analysis.reporting import print_dataset_comparison, print_feature_explanation


def main():

    parser = argparse.ArgumentParser(
        description="Random Forest Statistical Image Steganalysis Tool"
    )

    parser.add_argument("--image", help="Analyze single image")
    parser.add_argument("--folder", help="Analyze folder")

    args = parser.parse_args()

    tool = SteganalysisTool()

    print_feature_explanation(tool)

    if args.image:

        result = tool.analyze_image(args.image)

        if result:
            print_report(result)
            print_dataset_comparison(tool, result)

    elif args.folder:

        results = tool.analyze_folder(args.folder)

        for r in results:
            print_report(r)
            print_dataset_comparison(tool, r)

        print_summary(results)
        export_results(results)

    else:
        print("Specify --image or --folder")