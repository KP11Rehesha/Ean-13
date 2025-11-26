from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import messagebox


class EAN13ManualGenerator:
    def __init__(self):

        self.L_CODES = [
            "0001101", "0011001", "0010011", "0111101", "0100011",
            "0110001", "0101111", "0111011", "0110111", "0001011"
        ]
        self.G_CODES = [
            "0100111", "0110011", "0011011", "0100001", "0011101",
            "0111001", "0000101", "0010001", "0001001", "0010111"
        ]
        self.R_CODES = [
            "1110010", "1100110", "1101100", "1000010", "1011100",
            "1001110", "1010000", "1000100", "1001000", "1110100"
        ]


        self.PARITY_PATTERNS = [
            "LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
            "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"
        ]

    def calculate_check_digit(self, code_12):

        sum_odd = 0
        sum_even = 0


        for i, char in enumerate(code_12):
            digit = int(char)
            if (i + 1) % 2 != 0:
                sum_odd += digit
            else:
                sum_even += digit

        total = sum_odd + (sum_even * 3)
        remainder = total % 10
        if remainder == 0:
            return 0
        return 10 - remainder

    def encode(self, code_input):

        if len(code_input) != 12 or not code_input.isdigit():
            raise ValueError("Має бути 12 цифр")


        check_digit = self.calculate_check_digit(code_input)
        full_code = code_input + str(check_digit)


        first_digit = int(full_code[0])
        left_side_digits = full_code[1:7]
        right_side_digits = full_code[7:13]

        pattern = self.PARITY_PATTERNS[first_digit]


        binary_string = "101"


        for i, digit_char in enumerate(left_side_digits):
            digit = int(digit_char)
            encoding_type = pattern[i]
            if encoding_type == 'L':
                binary_string += self.L_CODES[digit]
            else:
                binary_string += self.G_CODES[digit]

        binary_string += "01010"


        for digit_char in right_side_digits:
            digit = int(digit_char)
            binary_string += self.R_CODES[digit]

        binary_string += "101"

        return full_code, binary_string

    def draw_barcode(self, code_input, filename="manual_barcode.png"):
        try:
            full_code, binary_string = self.encode(code_input)
        except ValueError as e:
            messagebox.showerror("Помилка", str(e))
            return


        module_width = 3
        height = 150
        quiet_zone = 30

        total_width = (len(binary_string) * module_width) + (2 * quiet_zone)


        img = Image.new('RGB', (total_width, height + 50), 'white')
        draw = ImageDraw.Draw(img)


        x = quiet_zone
        for bit in binary_string:
            if bit == '1':

                draw.rectangle([x, 10, x + module_width - 1, height], fill='black')
            x += module_width


        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()


        draw.text((5, height + 5), full_code[0], fill='black', font=font)


        text_part = full_code[1:]

        draw.text((quiet_zone + 20, height + 5), f"{text_part[:6]}   {text_part[6:]}", fill='black', font=font)

        img.save(filename)
        img.show()
        return full_code



def on_generate():
    code = entry.get()
    generator = EAN13ManualGenerator()
    result_code = generator.draw_barcode(code)
    if result_code:
        lbl_info.config(text=f"Згенеровано код: {result_code}")


root = tk.Tk()
root.title("EAN-13 Generator (Manual Logic)")
root.geometry("400x200")

tk.Label(root, text="Введіть 12 цифр:").pack(pady=10)
entry = tk.Entry(root)
entry.pack(pady=5)

btn = tk.Button(root, text="Створити штрих-код", command=on_generate)
btn.pack(pady=20)

lbl_info = tk.Label(root, text="")
lbl_info.pack()

root.mainloop()