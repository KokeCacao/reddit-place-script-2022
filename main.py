# imports
import os, random
import math
import requests
import json
import time
from io import BytesIO
from websocket import create_connection
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from PIL import ImageColor
from PIL import Image

# load env variables
load_dotenv()

# pixel drawing preferences
pixel_x_start = 1743
pixel_y_start = 664

# map of colors for pixels you can place
color_map = {
    "#BE0039": 1,  # put color here
    "#FF4500": 2,  # bright red
    "#FFA800": 3,  # orange
    "#FFD635": 4,  # yellow
    "#00A368": 6,  # darker green
    "#00CC78": 7,  # put color here
    "#7EED56": 8,  # lighter green
    "#00756F": 9,  # put color here
    "#009EAA": 10,  # put color here
    "#2450A4": 12,  # darkest blue
    "#3690EA": 13,  # medium normal blue
    "#51E9F4": 14,  # cyan
    "#493AC1": 15,  # put color here
    "#6A5CFF": 16,  # put color here
    "#811E9F": 18,  # darkest purple
    "#B44AC0": 19,  # normal purple
    "#FF3881": 22,  # put color here
    "#FF99AA": 23,  # pink
    "#6D482F": 24,  # put color here
    "#9C6926": 25,  # brown
    "#000000": 27,  # black
    "#898D90": 29,  # grey
    "#D4D7D9": 30,  # light grey
    "#FFFFFF": 31,  # white
}

def rgb_to_hex(rgb):
    return ('#%02x%02x%02x' % rgb).upper()


def closest_color(target_rgb, rgb_colors_array_in):
    #print(target_rgb)
    r, g, b, a = target_rgb
    #print(r,g,b,a)
    if a < 255 or (r,g,b) == (69,42,0):
        return (69,42,0)
    color_diffs = []
    for color in rgb_colors_array_in:
        cr, cg, cb = color
        color_diff = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        color_diffs.append((color_diff, color))
    return min(color_diffs)[1]


rgb_colors_array = []

for color_hex, color_index in color_map.items():
    rgb_array = ImageColor.getcolor(color_hex, "RGB")
    rgb_colors_array.append(rgb_array)

print("available colors (rgb): ", rgb_colors_array)

image_path = os.path.join(os.path.abspath(os.getcwd()), 'image.jpg')
im = Image.open(image_path)

pix = im.convert('RGBA').load()
print("image size: ", im.size)  # Get the width and hight of the image for iterating over
image_width, image_height = im.size

# test drawing image to file called new_image before drawing to r/place
current_r = 0
current_c = 0
pixels = 0

start_x, start_y = (0, 0)

while True:
    r = current_r
    c = current_c

    target_rgb = pix[r, c]
    new_rgb = closest_color(target_rgb, rgb_colors_array)
    # print("closest color: ", new_rgb)
    pix[r, c] = new_rgb
    if new_rgb != (69,42,0):
        if start_x == 0 and start_y == 0:
            start_x, start_y = r, c
        pixels += 1

    current_r += 1

    if current_r >= image_width:
        current_c += 1
        current_r = 0

    if current_c >= image_height:
        print("done drawing image locally to new_image.png")
        break

new_image_path = os.path.join(os.path.abspath(os.getcwd()), 'new_image.png')
im.save(new_image_path)

# developer's reddit username and password
#username = os.getenv('ENV_PLACE_USERNAME')
#password = os.getenv('ENV_PLACE_PASSWORD')
# note: use https://www.reddit.com/prefs/apps
#app_client_id = os.getenv('ENV_PLACE_APP_CLIENT_ID')
#secret_key = os.getenv('ENV_PLACE_SECRET_KEY')
accounts = {
}

# this is horrible, but i'm too lazy to make it not bad
def fill_accounts():
    print("aaaa",len(json.loads(os.getenv('ENV_PLACE_USERNAME'))),
        len(json.loads(os.getenv('ENV_PLACE_PASSWORD'))),
        len(json.loads(os.getenv('ENV_PLACE_APP_CLIENT_ID'))),
        len(json.loads(os.getenv('ENV_PLACE_SECRET_KEY'))))

    if len(json.loads(os.getenv('ENV_PLACE_USERNAME'))) != (len(json.loads(os.getenv('ENV_PLACE_USERNAME'))) + len(json.loads(os.getenv('ENV_PLACE_PASSWORD'))) + len(json.loads(os.getenv('ENV_PLACE_APP_CLIENT_ID'))) + len(json.loads(os.getenv('ENV_PLACE_SECRET_KEY'))))/4:
        print("Your .env file is messed up")
        quit()

    i = 0
    for name in json.loads(os.getenv('ENV_PLACE_USERNAME')):
        account = {
            "password": json.loads(os.getenv('ENV_PLACE_PASSWORD'))[i],
            "app_client_id": json.loads(os.getenv('ENV_PLACE_APP_CLIENT_ID'))[i],
            "secret_key": json.loads(os.getenv('ENV_PLACE_SECRET_KEY'))[i],
            "access_token": None,
            "access_token_type": "",
            "expires_at_timestamp": 0,
            "access_token_scope": "",
        }

        accounts[name] = account

        i += 1

# note: reddit limits us to place 1 pixel every 5 minutes, so I am setting it to 5 minutes and 30 seconds per pixel
pixel_place_frequency = 320

# global variables for script
access_token = None
current_timestamp = math.floor(time.time())
#last_time_placed_pixel = math.floor(time.time())-310 # Uncomment to make start instantly
access_token_expires_at_timestamp = math.floor(time.time())

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()

def get_valid_auth(name):
    #print(name,accounts[name])
    #print(accounts[name]['access_token'] is None, current_timestamp >= accounts[name]['expires_at_timestamp'])
    # refresh access token if necessary
    if accounts[name]['access_token'] is None or current_timestamp >= accounts[name]['expires_at_timestamp']:
        print("refreshing access token for",name,"...")

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_8_7 rv:5.0; en-US) AppleWebKit/533.31.5 (KHTML, like Gecko) Version/4.0 Safari/533.31.5',
        }

        data = {
            'grant_type': 'password',
            'username': name,
            'password': accounts[name]['password']
        }

        r = requests.post("https://ssl.reddit.com/api/v1/access_token",
                          data=data,
                          auth=HTTPBasicAuth(accounts[name]['app_client_id'], accounts[name]['secret_key']),
                          headers=headers)

        #print("received response: ", r.text)

        response_data = r.json()

        accounts[name]['access_token'] = response_data["access_token"]
        accounts[name]['access_token_type'] = response_data["token_type"]  # this is just "bearer"
        accounts[name]['expires_at_timestamp'] = current_timestamp + int(response_data["expires_in"])  # this is usually "3600"
        accounts[name]['access_token_scope'] = response_data["scope"]  # this is usually "*"

        print("received new access token: ", accounts[name]['access_token'])

def completeness(img):
    x = 0
    y= 0
    pix2 = img.convert('RGB').load()
    complete = 0
    while True:
        x += 1

        if x >= image_width:
            y += 1
            x = 0

        if y >= image_height:
            break;
            x = 0
            y = 0

        target_rgb = pix[x, y]
        new_rgb = closest_color(target_rgb, rgb_colors_array)
        if pix2[x+pixel_x_start,y+pixel_y_start] == new_rgb:
            #print(pix2[x+pixel_x_start,y+pixel_y_start], new_rgb,new_rgb != (69,42,0), pix2[x,y] != new_rgb)
            if new_rgb != (69,42,0):
                complete += 1#print("Different Pixel found at:",x+pixel_x_start,y+pixel_y_start,"With Color:",pix2[x+pixel_x_start,y+pixel_y_start],"Replacing with:",new_rgb)
                #pix2[x+pixel_x_start,y+pixel_y_start] = new_rgb
            else:
                pass#print("TransparrentPixel")
    printProgressBar(complete,pixels,'Image Progress:','Complete', length = 50)


fill_accounts()

error_count = 0
error_limit = 10

# method to draw a pixel at an x, y coordinate in r/place with a specific color
def set_pixel(access_token_in, x, y, color_index_in=18, canvas_index=0):
    global error_count
    global error_limit
    print("placing pixel")

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

    #print(response.text)
    if 'errors' in json.loads(response.text):
        print(response.text)
        error_count += 1
        if error_count > error_limit:
            print("Some thing bad has happened, you've passed the error limit")
        print("that's probably not good",error_count,"error(s)")
        print("next pixel in",((float(current_timestamp)-float(json.loads(response.text)['errors'][0]['extensions']['nextAvailablePixelTs'])/1000)),"seconds")

def get_board(bearer):
    print("Getting board")
    ws = create_connection("wss://gql-realtime-2.reddit.com/query")
    ws.send(json.dumps({"type":"connection_init","payload":{"Authorization":"Bearer "+bearer}}))
    ws.recv()
    ws.send(json.dumps({"id":"1","type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CONFIG"}}},"extensions":{},"operationName":"configuration","query":"subscription configuration($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on ConfigurationMessageData {\n          colorPalette {\n            colors {\n              hex\n              index\n              __typename\n            }\n            __typename\n          }\n          canvasConfigurations {\n            index\n            dx\n            dy\n            __typename\n          }\n          canvasWidth\n          canvasHeight\n          __typename\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))
    ws.recv()

    image_sizex = 2
    image_sizey = 1

    imgs = []
    already_added = []
    for i in range(0, image_sizex*image_sizey):
        ws.send(json.dumps({"id":str(2+i),"type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CANVAS","tag":str(i)}}},"extensions":{},"operationName":"replace","query":"subscription replace($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on FullFrameMessageData {\n          __typename\n          name\n          timestamp\n        }\n        ... on DiffFrameMessageData {\n          __typename\n          name\n          currentTimestamp\n          previousTimestamp\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))
        file = ""
        while True:
            temp = json.loads(ws.recv())
            #print("\n",temp)
            if temp['type'] == 'data':
                msg = temp['payload']['data']['subscribe']
                if msg['data']['__typename'] == 'FullFrameMessageData':
                    if not temp['id'] in already_added:
                        imgs.append(Image.open(BytesIO(requests.get(msg['data']['name'], stream = True).content)))
                        already_added.append(temp['id'])
                    break;
        ws.send(json.dumps({"id":str(2+i),"type":"stop"}))

    ws.close()

    #print("\n\n", already_added)


    new_im = Image.new('RGB', (1000*2, 1000))

    x_offset = 0
    for img in imgs:
        new_im.paste(img, (x_offset,0))
        x_offset += img.size[0]

    print("Got image:", file)

    return new_im

def get_unset_pixel(img):
    x = 0
    y= 0
    pix2 = img.convert('RGB').load()
    visited = []
    def fill(x,y,depth = 0):
        if depth > 20 or (x,y) in visited:
            return

        visited.append((x,y))
        target_rgb = pix[x, y]
        new_rgb = closest_color(target_rgb, rgb_colors_array)
        #if the square is not the new color
        if pix2[x+pixel_x_start,y+pixel_y_start] != new_rgb:
            #print(pix2[x+pixel_x_start,y+pixel_y_start], new_rgb,new_rgb != (69,42,0), pix2[x,y] != new_rgb)
            if new_rgb != (69,42,0):
                print("Different Pixel found at:",x+pixel_x_start,y+pixel_y_start,"With Color:",pix2[x+pixel_x_start,y+pixel_y_start],"Replacing with:",new_rgb,"Used Fill method")
                pix2[x+pixel_x_start,y+pixel_y_start] = new_rgb
                return x, y
        else:
            pass
        neighbors = [(x-1,y),(x+1,y),(x-1,y-1),(x+1,y+1),(x-1,y+1),(x+1,y-1),(x,y-1),(x,y+1)]
        for n in neighbors:
            if 0 <= n[0] <= image_width-1 and 0 <= n[1] <= image_height-1:
                r = fill(n[0],n[1],depth+1)
                if r != None:
                    return r

    pos = fill(start_x, start_y, 0)
    if pos == None:
        everything_done = False
        while True: # Old code
            x += 1

            if x >= image_width:
                y += 1
                x = 0

            if y >= image_height:
                everything_done = True
                x = 0
                y = 0

            #print(x+pixel_x_start,y+pixel_y_start)
            #print(x, y,"img",image_width,image_height)
            target_rgb = pix[x, y]
            new_rgb = closest_color(target_rgb, rgb_colors_array)
            if pix2[x+pixel_x_start,y+pixel_y_start] != new_rgb:
                #print(pix2[x+pixel_x_start,y+pixel_y_start], new_rgb,new_rgb != (69,42,0), pix2[x,y] != new_rgb)
                if new_rgb != (69,42,0):
                    print("Different Pixel found at:",x+pixel_x_start,y+pixel_y_start,"With Color:",pix2[x+pixel_x_start,y+pixel_y_start],"Replacing with:",new_rgb,"Used printer method")
                    pix2[x+pixel_x_start,y+pixel_y_start] = new_rgb
                    break;
                else:
                    pass#print("TransparrentPixel")
            elif everything_done:
                if new_rgb != (69,42,0):
                    print("Nothing to do")
                    time.sleep(30)
                    pix2[x+pixel_x_start,y+pixel_y_start] = new_rgb
                    break;
                else:
                    pass#print("TransparrentPixel")
    else:
        x,y = pos
    return x,y

# current pixel row and pixel column being drawn
current_r = 0
current_c = 0

# loop to keep refreshing tokens when necessary and to draw pixels when the time is right
while True:
    placing = False

    #does things
    for name, info in accounts.items():
        current_timestamp = math.floor(time.time())
        get_valid_auth(name)

        # draw pixel onto screen
        if info['access_token'] is not None:# and (current_timestamp >= last_time_placed_pixel + pixel_place_frequency or placing):
            # get current pixel position from input image

            # this is probably really bad, and reddit will probably not like it
            # I need to update this to be better, but i am lazy
            board = get_board(info['access_token'])
            r, c = get_unset_pixel(board)

            target_rgb = pix[r, c]
            # get converted color
            new_rgb = closest_color(target_rgb, rgb_colors_array)
            new_rgb_hex = rgb_to_hex(new_rgb)
            pixel_color_index = color_map[new_rgb_hex]

            print("\nAccount Placing: ",name,"\n")

            # draw the pixel onto r/place
            #There's a better way to do this
            canvas = 0
            pixelx = pixel_x_start + r
            pixely = pixel_y_start + c
            while pixelx > 999:
                pixelx -= 1000
                canvas += 1

            try:
                set_pixel(info['access_token'], pixelx, pixely, pixel_color_index, canvas)
            except Exception as e:
                print(e)

            completeness(board)
            print("\n")

            if not placing:
                last_time_placed_pixel = math.floor(time.time())

            placing = True

        time.sleep((pixel_place_frequency/len(accounts))+1)
    time.sleep(10)