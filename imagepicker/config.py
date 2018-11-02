import re
from os.path import expanduser

# browser
# The path of geckodriver file
executable_path='your_path'
# The path of firefox command file
firefox_binary='/usr/bin/firefox'
# The path of profile folder
firefox_profile='your_firefox_profile'

# DuckDuckGo search image url and xpaths
ddg_searchimage_url = 'https://duckduckgo.com/?q=%s&t=h_&iax=images&ia=images'
# locate element that attribute style contains 'transform: translateX(0px);'
ddg_image_xpath = ".//div[@id='zci-images']/div[2]/div[@class='detail__wrap']/div[1]/div[contains(@style, 'transform: translateX(0px);')]/div/div[1]/div/a"
ddg_heading_xpath = ".//div[@id='zci-images']/div[2]/div[@class='detail__wrap']/div[1]/div[contains(@style, 'transform: translateX(0px);')]/div/div[2]/div/h5/a"
title_xpath = "/html/head/title"
# xpath of close slider button
ddg_image_detail_slider_xpath = './/*[@id="zci-images"]/div[2]/div/i'
# image thumbnail of ddg
ddg_image_thumbnail_xpath = ".//*[@id='zci-images']/div[2]/div/div[1]/div[@class='detail__pane' and contains(@style, 'transform: translateX(0px);')]/div/div[1]/div/a/img[1]"

# only_image_thumbnail = True

# anki
# import image info into 'reminder' field
image_field_name = 'reminder'
shortcut = 'Ctrl+G'

# set proxy, can be keep blank if unnecessary
# SOCKS4: 1 SOCKS5: 2 HTTP: 3
protocol = 2
server = '127.0.0.1'
port = '8086'

# In user home by default
log_file = 'image-picker.log'
