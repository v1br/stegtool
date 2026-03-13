import argparse

from src.detector import SteganalysisTool
from src.embedder import LSBEmbedder
from src.extractor import LSBExtractor

from src.analysis.reporting import (
    print_report,
    print_summary,
    export_results,
    print_dataset_comparison,
    print_feature_explanation
)


def main():

    parser = argparse.ArgumentParser(
        description="Image LSB Tool"
    )

    # Detection arguments
    parser.add_argument("--image", help="Analyze single image")
    parser.add_argument("--folder", help="Analyze folder")

    # Embed arguments
    parser.add_argument("--embed", action="store_true",
                        help="Embed text into image")

    parser.add_argument("--input", help="Input cover image")
    parser.add_argument("--output", help="Output stego image")
    parser.add_argument("--text", help="Text message to embed")

    parser.add_argument("--payload", type=float, default=0.3,
                        help="Payload size (0.1 – 0.5 bpp)")

    parser.add_argument("--analyze", action="store_true",
                        help="Analyze generated stego image")

    # Extract argument
    parser.add_argument("--extract", help="Extract hidden message from image")

    args = parser.parse_args()

    # -----------------------------------------------------
    # EMBED MODE
    # -----------------------------------------------------

    if args.embed:

        if not args.input or not args.output or not args.text:
            print("Embed mode requires --input --output --text")
            return

        embedder = LSBEmbedder()

        print("\nEmbedding message...\n")

        stego_path = embedder.embed(
            image_path=args.input,
            output_path=args.output,
            text=args.text,
            payload_bpp=args.payload
        )

        print("\nStego image created:", stego_path)

        if args.analyze:

            print("\nRunning detection on generated image...\n")

            tool = SteganalysisTool()

            print_feature_explanation(tool)

            result = tool.analyze_image(stego_path)

            if result:
                print_report(result)
                print_dataset_comparison(tool, result)

        return

    # -----------------------------------------------------
    # EXTRACT MODE
    # -----------------------------------------------------

    if args.extract:

        extractor = LSBExtractor()

        print("\nExtracting hidden message...\n")

        try:
            message = extractor.extract(args.extract)

            if message:
                print("Hidden message:")
                print("--------------------------------")
                print(message)
                print("--------------------------------")
            else:
                print("No message extracted.")

        except Exception as e:
            print("Extraction failed:", e)

        return

    # -----------------------------------------------------
    # DETECTION MODE
    # -----------------------------------------------------

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
        print("Specify --image, --folder, --embed, or --extract")


if __name__ == "__main__":
    main()