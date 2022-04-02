# imports
import os
import math
import requests
import json
import time
import threading
from io import BytesIO
from websocket import create_connection
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from PIL import ImageColor
from PIL import Image
import random
import sys

# load env variables
load_dotenv()

# map of colors for pixels you can place
color_map = {
    "#FF4500": 2,  # bright red
    "#FFA800": 3,  # orange
    "#FFD635": 4,  # yellow
    "#00A368": 6,  # darker green
    "#7EED56": 8,  # lighter green
    "#2450A4": 12,  # darkest blue
    "#3690EA": 13,  # medium normal blue
    "#51E9F4": 14,  # cyan
    "#811E9F": 18,  # darkest purple
    "#B44AC0": 19,  # normal purple
    "#FF99AA": 23,  # pink
    "#9C6926": 25,  # brown
    "#000000": 27,  # black
    "#898D90": 29,  # grey
    "#D4D7D9": 30,  # light grey
    "#FFFFFF": 31,  # white
}

# color palette
rgb_colors_array = []

# auth variables
access_tokens = []
access_token_expires_at_timestamp = []

# image.jpg information
pix = None
image_width = None
image_height = None

# place a pixel immediately
# first_run = True
first_run_counter = 0

# function to convert rgb tuple to hexadecimal string
def rgb_to_hex(rgb):
    return ('#%02x%02x%02x' % rgb).upper()


# function to find the closest rgb color from palette to a target rgb color
def closest_color(target_rgb, rgb_colors_array_in):
    r, g, b = target_rgb
    color_diffs = []
    for color in rgb_colors_array_in:
        cr, cg, cb = color
        color_diff = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        color_diffs.append((color_diff, color))
    return min(color_diffs)[1]


# method to draw a pixel at an x, y coordinate in r/place with a specific color
def set_pixel(access_token_in, x, y, color_index_in=18, canvas_index=0):
    print("placing pixel with color index " + str(color_index_in) + " at " + str((x, y)))

    url = "https://gql-realtime-2.reddit.com/query"

    payload = json.dumps({
        "operationName": "setPixel",
        "variables": {
            "input": {
                "actionName": "r/replace:set_pixel",
                "PixelMessageData": {
                    "coordinate": {
                        "x": x,
                        "y": y
                    },
                    "colorIndex": color_index_in,
                    "canvasIndex": canvas_index
                }
            }
        },
        "query": "mutation setPixel($input: ActInput!) {\n  act(input: $input) {\n    data {\n      ... on BasicMessage {\n        id\n        data {\n          ... on GetUserCooldownResponseMessageData {\n            nextAvailablePixelTimestamp\n            __typename\n          }\n          ... on SetPixelResponseMessageData {\n            timestamp\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
    })
    headers = {
        'origin': 'https://hot-potato.reddit.com',
        'referer': 'https://hot-potato.reddit.com/',
        'apollographql-client-name': 'mona-lisa',
        'Authorization': 'Bearer ' + access_token_in,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print("received response: ", response.text)

def get_board(access_token_in):
    print("Getting board")
    ws = create_connection("wss://gql-realtime-2.reddit.com/query")
    ws.send(json.dumps({"type":"connection_init","payload":{"Authorization":"Bearer "+ access_token_in}}))
    ws.recv()
    ws.send(json.dumps({"id":"1","type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CONFIG"}}},"extensions":{},"operationName":"configuration","query":"subscription configuration($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on ConfigurationMessageData {\n          colorPalette {\n            colors {\n              hex\n              index\n              __typename\n            }\n            __typename\n          }\n          canvasConfigurations {\n            index\n            dx\n            dy\n            __typename\n          }\n          canvasWidth\n          canvasHeight\n          __typename\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))
    ws.recv()
    ws.send(json.dumps({"id":"2","type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CANVAS","tag":"0"}}},"extensions":{},"operationName":"replace","query":"subscription replace($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on FullFrameMessageData {\n          __typename\n          name\n          timestamp\n        }\n        ... on DiffFrameMessageData {\n          __typename\n          name\n          currentTimestamp\n          previousTimestamp\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))

    file = ""
    while True:
        temp = json.loads(ws.recv())
        if temp['type'] == 'data':
            msg = temp['payload']['data']['subscribe']
            if msg['data']['__typename'] == 'FullFrameMessageData':
                file = msg['data']['name']
                break;


    ws.close()

    boardimg = BytesIO(requests.get(file, stream = True).content)
    print("Got image:", file)

    return boardimg

def get_unset_pixel(boardimg, x, y):
    x = 0
    y= 0
    pixel_x_start = int(os.getenv('ENV_DRAW_X_START'))
    pixel_y_start = int(os.getenv('ENV_DRAW_Y_START'))
    pix2 = Image.open(boardimg).convert('RGB').load()
    while True:
        x += 1

        if x >= image_width:
            y += 1
            x = 0

        if y >= image_height:
            break;

        print(x+pixel_x_start,y+pixel_y_start)
        print(x, y,"boardimg",image_width,image_height)
        target_rgb = pix[x, y]
        new_rgb = closest_color(target_rgb, rgb_colors_array)
        if pix2[x+pixel_x_start,y+pixel_y_start] != new_rgb:
            print(pix2[x+pixel_x_start,y+pixel_y_start], new_rgb,new_rgb != (69,42,0), pix2[x,y] != new_rgb)
            if new_rgb != (69,42,0):
                print("Different Pixel found at:",x+pixel_x_start,y+pixel_y_start,"With Color:",pix2[x+pixel_x_start,y+pixel_y_start],"Replacing with:",new_rgb)
                break;
            else:
                print("TransparrentPixel")
    return x,y

# method to define the color palette array
def init_rgb_colors_array():
    global rgb_colors_array

    # generate array of available rgb colors we can use
    for color_hex, color_index in color_map.items():
        rgb_array = ImageColor.getcolor(color_hex, "RGB")
        rgb_colors_array.append(rgb_array)

    print("available colors for palette (rgb): ", rgb_colors_array)


# method to read the input image.jpg file
def load_image():
    global pix
    global image_width
    global image_height
    # read and load the image to draw and get its dimensions
    image_path = os.path.join(os.path.abspath(os.getcwd()), 'image.jpg')
    im = Image.open(image_path)
    pix = im.load()
    print("image size: ", im.size)  # Get the width and height of the image for iterating over
    image_width, image_height = im.size


# task to draw the input image
def task(credentials_index):
    # whether image should keep drawing itself
    repeat_forever = True

    while True:
        # try:
        # global variables for script
        last_time_placed_pixel = math.floor(time.time())

        # note: reddit limits us to place 1 pixel every 5 minutes, so I am setting it to
        # 5 minutes and 30 seconds per pixel
        pixel_place_frequency = 330

        # pixel drawing preferences
        pixel_x_start = int(os.getenv('ENV_DRAW_X_START'))
        pixel_y_start = int(os.getenv('ENV_DRAW_Y_START'))

        # current pixel row and pixel column being drawn
        current_r = int(json.loads(os.getenv('ENV_R_START'))[credentials_index])
        current_c = int(json.loads(os.getenv('ENV_C_START'))[credentials_index])

        # string for time until next pixel is drawn
        update_str = ""

        # reference to globally shared variables such as auth token and image
        global access_tokens
        global access_token_expires_at_timestamp

        # boolean to place a pixel the moment the script is first run
        # global first_run
        global first_run_counter

        # refresh auth tokens and / or draw a pixel
        while True:
            # reduce CPU usage
            time.sleep(1)

            # get the current time
            current_timestamp = math.floor(time.time())

            # log next time until drawing
            time_until_next_draw = last_time_placed_pixel + pixel_place_frequency - current_timestamp
            new_update_str = str(time_until_next_draw) + " seconds until next pixel is drawn"
            if update_str != new_update_str:
                update_str = new_update_str
                # print("__________________")
                # print("Thread #" + str(credentials_index))
                print(update_str)
                sys.stdout.write("\033[F")
                # print("__________________")

            # refresh access token if necessary
            if access_tokens[credentials_index] is None or current_timestamp >= access_token_expires_at_timestamp[
                credentials_index]:
                print("__________________")
                print("Thread #" + str(credentials_index))
                print("refreshing access token...")

                # developer's reddit username and password
                username = json.loads(os.getenv('ENV_PLACE_USERNAME'))[credentials_index]
                password = json.loads(os.getenv('ENV_PLACE_PASSWORD'))[credentials_index]
                # note: use https://www.reddit.com/prefs/apps
                app_client_id = json.loads(os.getenv('ENV_PLACE_APP_CLIENT_ID'))[credentials_index]
                secret_key = json.loads(os.getenv('ENV_PLACE_SECRET_KEY'))[credentials_index]

                data = {
                    'grant_type': 'password',
                    'username': username,
                    'password': password
                }

                r = requests.post("https://ssl.reddit.com/api/v1/access_token",
                                  data=data,
                                  auth=HTTPBasicAuth(app_client_id, secret_key),
                                  headers={'User-agent': f'placebot{random.randint(1, 100000)}'})

                print("received response: ", r.text)

                response_data = r.json()
                access_tokens[credentials_index] = response_data["access_token"]
                # access_token_type = response_data["token_type"]  # this is just "bearer"
                access_token_expires_in_seconds = response_data["expires_in"]  # this is usually "3600"
                # access_token_scope = response_data["scope"]  # this is usually "*"

                # ts stores the time in seconds
                access_token_expires_at_timestamp[credentials_index] = current_timestamp \
                                                                       + int(access_token_expires_in_seconds)

                print("received new access token: ", access_tokens[credentials_index])
                print("__________________")

            # draw pixel onto screen
            if access_tokens[credentials_index] is not None and (current_timestamp >= last_time_placed_pixel
                                                                 + pixel_place_frequency or first_run_counter==0):
                
                
                # place pixel immediately
                # first_run = False
                first_run_counter += 1

                # get target color
                target_rgb = pix[current_r, current_c]

                # get converted color
                new_rgb = closest_color(target_rgb, rgb_colors_array)
                new_rgb_hex = rgb_to_hex(new_rgb)
                pixel_color_index = color_map[new_rgb_hex]

                # get current pixel position from input image
                current_r, current_c = get_unset_pixel(get_board(access_tokens[credentials_index]), pixel_x_start + current_r,
                          pixel_y_start + current_c)

                # draw the pixel onto r/place
                set_pixel(access_tokens[credentials_index], pixel_x_start + current_r,
                          pixel_y_start + current_c, pixel_color_index)
                last_time_placed_pixel = math.floor(time.time())


                # current_r = random.randint(0, image_width)
                # current_c = random.randint(0, image_height)
                current_r += 1

                # go back to first column when reached end of a row while drawing
                if current_r >= image_width:
                    current_r = 0
                    current_c += 1

                # exit when all pixels drawn
                if current_c >= image_height:
                    print("__________________")
                    print("Thread #" + str(credentials_index))
                    print("done drawing image to r/place")
                    print("__________________")
                    break
        # except:
        #     print("__________________")
        #     print("Thread #" + str(credentials_index))
        #     print("Error refreshing tokens or drawing pixel")
        #     print("Trying again in 5 minutes...")
        #     print("__________________")
        #     time.sleep(5 * 60)

        if not repeat_forever:
            break


# get color palette
init_rgb_colors_array()

# load the pixels for the input image
load_image()

# get number of concurrent threads to start
num_credentials = len(json.loads(os.getenv('ENV_PLACE_USERNAME')))

# define delay between starting new threads
delay_between_launches_seconds = 0

# launch a thread for each account specified in .env
for i in range(num_credentials):
    # run the image drawing task
    access_tokens.append(None)
    access_token_expires_at_timestamp.append(math.floor(time.time()))
    thread1 = threading.Thread(target=task, args=[i])
    thread1.start()
    time.sleep(delay_between_launches_seconds)