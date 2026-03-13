import cv2


class LSBExtractor:

    def preprocess_image(self, path):

        img = cv2.imread(path)

        if img is None:
            raise RuntimeError("Failed to load image")

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        img = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)

        return img

    # ---------------------------------------------

    def bits_to_int(self, bits):
        return int("".join(str(b) for b in bits), 2)

    # ---------------------------------------------

    def bits_to_text(self, bits):

        chars = []

        for i in range(0, len(bits), 8):

            byte = bits[i:i + 8]

            if len(byte) < 8:
                break

            value = int("".join(str(b) for b in byte), 2)

            chars.append(chr(value))

        return "".join(chars)

    # ---------------------------------------------

    def extract(self, image_path):

        img = self.preprocess_image(image_path)

        pixels = img.flatten()

        # read LSBs
        bits = [(p & 1) for p in pixels]

        # first 32 bits = message length
        length_bits = bits[:32]

        message_length = self.bits_to_int(length_bits)

        if message_length <= 0:
            print("No hidden message detected")
            return ""

        message_bits = bits[32:32 + message_length]

        message = self.bits_to_text(message_bits)

        return message