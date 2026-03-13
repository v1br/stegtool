import os
import argparse
import cv2


def convert_dataset(input_root, output_root):

    count = 0

    for root, dirs, files in os.walk(input_root):

        # compute relative folder path
        rel_path = os.path.relpath(root, input_root)

        # replicate directory structure
        output_dir = os.path.join(output_root, rel_path)

        os.makedirs(output_dir, exist_ok=True)

        for file in files:

            if file.lower().endswith(".pgm"):

                input_path = os.path.join(root, file)

                output_name = os.path.splitext(file)[0] + ".png"

                output_path = os.path.join(output_dir, output_name)

                img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)

                if img is None:
                    print("Skipping unreadable:", input_path)
                    continue

                cv2.imwrite(output_path, img)

                count += 1

                if count % 100 == 0:
                    print(f"Converted {count} images...")

    print("\nConversion complete.")
    print("Total images converted:", count)


def main():

    parser = argparse.ArgumentParser(
        description="Convert PGM dataset to PNG while preserving folder structure"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Root folder containing PGM images"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output folder for PNG images"
    )

    args = parser.parse_args()

    convert_dataset(args.input, args.output)


if __name__ == "__main__":
    main()