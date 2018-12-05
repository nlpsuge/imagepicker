# imagepicker
An add-on of searching word and importing image(s) for Anki. 

By using Selenium with geckodriver.

This anki-addon maybe useful for those people who want to search image(s) on Internet and import image(s) into Anki automatically when learning by using Anki. But the add-on only can do this things semi automatically. You must click one image, this add-on can recognise this image is needed to download and import into Anki. I'm thinking how to do it automatically.

No GUI. You can setup your environment in config.py. The most logic is in core.py.

Tested in Fedora 28/29. CentOS 7 should be OK. Have no time to test on other system operations yet.

Support to set proxy for dowloading imgage or obtaining the title of related article in config.py. Leave 'protocol' or 'server' or 'port' empty to avoid using proxy. You can use SwitchyOmega(https://github.com/FelisCatus/SwitchyOmega) when search images on DuckDuckGo.

