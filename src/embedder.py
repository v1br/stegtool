import cv2
import numpy as np
import random


class LSBEmbedder:

    def preprocess_image(self, path):

        img = cv2.imread(path)

        if img is None:
            raise RuntimeError("Failed to load image")

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        img = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)

        return img

    # -----------------------------------------

    def int_to_bits(self, value, bit_count):
        return [int(b) for b in format(value, f"0{bit_count}b")]

    # -----------------------------------------

    def text_to_bits(self, text):

        bits = []

        for c in text:
            bits.extend([int(b) for b in format(ord(c), "08b")])

        return bits

    # -----------------------------------------

    def embed(self, image_path, output_path, text, payload_bpp=0.3):

        img = self.preprocess_image(image_path)

        pixels = img.flatten()

        capacity = int(len(pixels) * payload_bpp)

        message_bits = self.text_to_bits(text)

        length_bits = self.int_to_bits(len(message_bits), 32)

        payload = length_bits + message_bits

        if len(payload) > capacity:
            raise RuntimeError("Message too large for selected payload")

        remaining = capacity - len(payload)

        payload += [random.randint(0, 1) for _ in range(remaining)]

        # embed sequentially
        for i, bit in enumerate(payload):
            pixels[i] = (pixels[i] & ~1) | bit

        stego = pixels.reshape(img.shape)

        cv2.imwrite(output_path, stego)

        print("Stego image saved:", output_path)

        return output_path