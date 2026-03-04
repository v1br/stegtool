import os
import cv2
import numpy as np
import argparse
import random
import string


def text_to_bits(text):
    bits = []
    for c in text:
        b = format(ord(c), "08b")
        bits.extend(int(bit) for bit in b)
    return bits


def generate_payload_bits(num_bits):
    text = "".join(random.choices(string.ascii_letters + string.digits, k=32))

    bits = []

    while len(bits) < num_bits:
        bits.extend(text_to_bits(text))

    return bits[:num_bits]


def embed_lsb(img, bits):

    h, w = img.shape
    pixels = img.flatten()

    if len(bits) > len(pixels):
        raise ValueError("Payload too large")

    for i in range(len(bits)):
        pixels[i] = (pixels[i] & ~1) | bits[i]

    return pixels.reshape(h, w)


def preprocess_image(path):

    img = cv2.imread(path)

    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(gray, (512, 512))

    return gray


def generate_dataset(input_folder, output_folder):

    payloads = [0.1, 0.2, 0.3, 0.4, 0.5]

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(os.path.join(output_folder, "cover"), exist_ok=True)

    for p in payloads:
        os.makedirs(os.path.join(output_folder, f"stego_{p}bpp"), exist_ok=True)

    images = [f for f in os.listdir(input_folder)
              if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]

    for img_name in images:

        path = os.path.join(input_folder, img_name)

        img = preprocess_image(path)

        if img is None:
            continue

        base_name = os.path.splitext(img_name)[0]

        cover_path = os.path.join(output_folder, "cover", base_name + ".png")
        cv2.imwrite(cover_path, img)

        pixels = img.shape[0] * img.shape[1]

        for p in payloads:

            bits_needed = int(pixels * p)

            payload_bits = generate_payload_bits(bits_needed)

            stego_img = embed_lsb(img.copy(), payload_bits)

            out_path = os.path.join(
                output_folder,
                f"stego_{p}bpp",
                f"{base_name}_{p}bpp.png"
            )

            cv2.imwrite(out_path, stego_img)

        print("Processed:", img_name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True, help="Folder with cover images")
    parser.add_argument("--output", default="stego_dataset", help="Output dataset folder")

    args = parser.parse_args()

    generate_dataset(args.input, args.output)

    print("\nDataset generation complete.")