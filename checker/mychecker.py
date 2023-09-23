#!/usr/bin/env python3

from ctf_gameserver import checkerlib

from PIL import Image, ImageDraw, UnidentifiedImageError, ImageFont
from io import BytesIO
from hashlib import sha256
import numpy as np
import requests
import logging
import secrets
import os

import utils

CANVAS_PATH = os.path.join(os.path.dirname(__file__), "canvas.jpg")

# initialize empty list for galleries
galleries = []

# create gallery tuple for fun type gallery
galleries.append(('Hey party people! Do you remember what Michael did during that crazy night, when we were out?!? I just found some pictures on my iPhone that I can\'t even remember having taken... Don\'t tease him too much, OK? ;)', ['./fun/2020-10-09_22-46-01_fun1.jpg', './fun/2020-10-09_23-15-27_fun2.jpg', './fun/2020-10-10_14-22-33_recovery.jpg']))

# create gallery tuple for view type gallery
galleries.append(('Welcome folks! Here, I share with you a collection of the wonderful places I have been during my trip around the world. Be ready to be struck with awe!', ['./view/2017-09-06_19-46-25_rainbow.jpg', './view/2020-09-01_18-02-56_view.jpg', './view/2020-10-09_10-06-53_tree-house.jpg']))

# create gallery tuple for beach type gallery
galleries.append(('The sun, a perfect beach, and the sound of waves... Is there anything better to relax than this combination? Ok, add a chilled glass of Mojito and you don\'t remember what the word \'stress\' means.', ['./beach/2018-04-18_16-59-33_beach.jpg', './beach/2021-07-11_12-56-14_beach.jpg', './beach/2021-09-05_11-15-33_beach.jpg', './beach/2022-07-28_12-24-13_beach.jpg']))

# create gallery tuple for mysterious type gallery
galleries.append(('The best thing about traveling is that one sees so many wonderous places, which leave you wondering: \'How can this be possible?\' Here is a small selection of crazy locations I have seen.', ['./mysterious/2016-03-15_21-34-03_minecraft_cave.jpg', './mysterious/2021-04-06_14-54-07_waterfall.jpg', './mysterious/2022-03-18_14-22-07_bridge.jpg', './mysterious/2023-02-28_15-32-12_wicked-trees.jpg']))

# create gallery tuple for plane type gallery
galleries.append(('Do you know what is my highlight when traveling? All the awesome airplanes you get to see and board. I don\'t care if it\'s an Airbus, Boeing, or Bombardier. As long as it has wings, jets, landing gear and enough power to glide through the air, I am hooked. Send me an email and ask for the password if you are a plane nerd like me! :)', ['./plane/2017-02-13_15-05-23_onboard.jpg', './plane/2019-12-03_18-46-39_boarding.jpg', './plane/2022-06-23_13-48-09_landing.jpg', './plane/2023-01-02_08-07-27_takeoff.jpg']))


def generateFlagImage(flag):
    font = ImageFont.truetype("/usr/share/fonts/truetype/open-sans/OpenSans-Regular.ttf", size=11)
    image = Image.open(CANVAS_PATH)
    draw = ImageDraw.Draw(image)
    draw.text((70, 80), flag, fill =(1, 1, 1), font=font)

    sha256_sum = sha256(bytes(np.array(image).flatten()))

    # image.save('./output.png')
    return image, sha256_sum


class ImageGaloisryChecker(checkerlib.BaseChecker):
    def base_url(self):
        return f'http://[{self.ip}]:5005'

    def createGallery(self, gallery_name, description, password):
        logging.info(f"Creating gallery {gallery_name} with description {description} and password {password}")
        url = self.base_url() + '/create'
        form_data = {'gallery_name': gallery_name, 'description': description, 'password': password}
        response = requests.post(url, data = form_data)
        if response.status_code != 200:
            try:
                logging.error(f"create Gallery failed: {response.text}")
            except AttributeError:
                logging.error(f"create Gallery failed: {response.content}")
        return response.status_code == 200

    def uploadImage(self, gallery_name, file_name, image):
        logging.info(f'Uploading image to gallery {gallery_name}')
        url = self.base_url() + '/gallery/' + gallery_name + '/upload'

        byte_io = BytesIO()
        image.save(byte_io, 'png')
        byte_io.seek(0)

        file = {'mediafile': (file_name, byte_io, 'image/png')}

        response = requests.post(url, files = file)
        if response.status_code != 200:
            try:
                logging.error(f"upload Image failed: {response.text}")
            except AttributeError:
                logging.error(f"upload Image failed: {response.content}")
        return response.status_code == 200

    def decryptImage(self, gallery_name, file_name, password):
        logging.info(f'Decrypting image {file_name} from {gallery_name} with password {password}')
        url = self.base_url() + '/gallery/' + gallery_name + '/decrypt'

        json_data = {'fileId': file_name, 'password': password}
        image_response = requests.post(url, json = json_data)
        if image_response.status_code != 200:
            logging.error('Decryption failed')
            return False, None
        try:
            image = Image.open(BytesIO(image_response.content))
        except UnidentifiedImageError:
            logging.error('Invalid image')
            return False

        sha256_sum = sha256(bytes(np.array(image).flatten()))

        return image, sha256_sum

    def downloadImage(self, gallery_name, file_name):
        logging.info(f'Downloading image {file_name} from {gallery_name}')
        url = self.base_url() + '/gallery/' + gallery_name + '/download/' + file_name
        image_response = requests.get(url)
        if image_response.status_code != 200:
            try:
                logging.error(f"download Image failed: {image_response.text}")
            except AttributeError:
                logging.error(f"download Image failed: {image_response.content}")
        if image_response.status_code != 200:
            logging.error('Download failed')
            return False
        try:
            image = Image.open(BytesIO(image_response.content))
        except UnidentifiedImageError:
            logging.error('Invalid image')
            return False
        return image

    def place_flag(self, tick):
        gallery_name = secrets.token_hex(16)
        file_flag_name = f'flag{secrets.token_hex(8)}.png'

        # choose a random gallery type
        gallery = galleries[secrets.randbelow(5)]
        description = gallery[0]
        file_names = gallery[1]

        password = secrets.token_hex(16)
        flag = checkerlib.get_flag(tick)

        # create gallery
        if not self.createGallery(gallery_name, description, password):
            logging.error("Gallery creation failed")
            return checkerlib.CheckResult.FAULTY

        logging.info("Generating flag...")
        # generate flag image
        flag_image, sha256_sum = generateFlagImage(flag)

        checkerlib.store_state(str(tick), (gallery_name, file_flag_name, password, sha256_sum.hexdigest()))
        checkerlib.set_flagid(f'{{"gallery": "{gallery_name}", "filename": "{file_flag_name}"}}')

        # upload additional images for fun
        for file_name in file_names:
            file_path = os.path.join(os.path.dirname(__file__), file_name)
            image = Image.open(file_path)
            self.uploadImage(gallery_name, file_name.split('/')[-1], image)
        
        # upload flag image
        self.uploadImage(gallery_name, file_flag_name, flag_image)
        return checkerlib.CheckResult.OK

    def check_service(self):
        gallery_name = secrets.token_hex(16)
        description = utils.generate_message()
        password = secrets.token_hex(16)
        if not self.createGallery(gallery_name, description, password):
            logging.error("Gallery creation failed")
            return checkerlib.CheckResult.FAULTY

        # check that our just created gallery is listed
        galleries = requests.get(self.base_url() + '/').content
        if f'<a href="/gallery/{gallery_name}">'.encode() not in galleries:
            try:
                logging.error(f"Gallery doesn't show up in listing: {galleries.decode()}")
            except AttributeError:
                logging.error(f"Gallery doesn't show up in listing: {galleries}")
            return checkerlib.CheckResult.FAULTY

        # upload test image
        file_name = secrets.token_hex(8 + secrets.randbelow(8)) + '.png'
        image, _ = generateFlagImage(secrets.token_hex(8))
        self.uploadImage(gallery_name, file_name, image)

        # Check that test image is there
        gallerycontent = requests.get(self.base_url() + f'/gallery/{gallery_name}').content
        if f'<span class="file-name">{file_name}</span>'.encode() not in gallerycontent:
            try:
                logging.error(f"Uploaded file is not in gallery listing: {gallerycontent.decode()}")
            except AttributeError:
                logging.error(f"Uploaded file is not in gallery listing: {gallerycontent}")
            return checkerlib.CheckResult.FAULTY

        # delete test image
        delete = requests.post(self.base_url() + f'/gallery/{gallery_name}/delete', json={'fileId': file_name, 'password': password})
        if delete.status_code != 200:
            try:
                logging.warn(f"Deletion output: {delete.text}")
            except AttributeError:
                logging.warn(f"Deletion output: {delete.content}")

        # Check that test image is not there anymore
        gallerycontent = requests.get(self.base_url() + f'/gallery/{gallery_name}').content
        if f'<span class="file-name">{file_name}</span>'.encode() in gallerycontent:
            try:
                logging.error(f"Uploaded file is still in gallery listing: {gallerycontent.decode()}")
            except UnicodeDecodeError:
                logging.error(f"Uploaded file is still in gallery listing: {gallerycontent}")
            return checkerlib.CheckResult.FAULTY

        logging.info(f'Deleting gallery gallery {gallery_name}')
        url = self.base_url() + '/gallery/' + gallery_name + '/delete_gal'

        response = requests.post(url, json={'password': password})
        if response.status_code != 200:
            try:
                logging.error(f"deleting gallery failed: {response.text}")
            except AttributeError:
                logging.error(f"deleting gallery failed: {response.content}")

        # check that our deleted gallery isn't listed
        galleries = requests.get(self.base_url() + '/').content
        if f'<a href="/gallery/{gallery_name}">'.encode() in galleries:
            try:
                logging.error(f"Deleted gallery still shows up in listing: {galleries.decode()}")
            except AttributeError:
                logging.error(f"Deleted gallery still shows up in listing: {galleries}")
            return checkerlib.CheckResult.FAULTY

        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        file_name = secrets.token_hex(16)
        state = checkerlib.load_state(str(tick))
        if not state:
            # Flag placement was not successful in the tick to check
            logging.warn('Failed to load state')
            return checkerlib.CheckResult.FLAG_NOT_FOUND
        (gallery_name, file_name, password, sha256_sum) = state
        # download encrypted flag image
        encrypted_image = self.downloadImage(gallery_name, file_name)
        if not encrypted_image:
            logging.error("Failed to download image")
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        # decrypt flag image
        decrypted_image, sha256_sum_decrypted = self.decryptImage(gallery_name, file_name, password)
        if sha256_sum_decrypted:
            sha256_sum_decrypted = sha256_sum_decrypted.hexdigest()

        if sha256_sum_decrypted == sha256_sum:
            return checkerlib.CheckResult.OK
        else:
            logging.error(f"flag hash does not match, expected {sha256_sum} got {sha256_sum_decrypted}")
            return checkerlib.CheckResult.FLAG_NOT_FOUND


if __name__ == '__main__':

    checkerlib.run_check(ImageGaloisryChecker)
