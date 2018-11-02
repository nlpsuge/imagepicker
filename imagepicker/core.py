# -*- coding: utf-8 -*-
import os
import socket
import thread
import threading

# fix ImportError: No module named 'module_name'
import sys
sys.path.append('/usr/lib/python2.7/site-packages')
sys.path.append('/usr/lib64/python2.7/site-packages')
sys.path.append('/usr/lib64/python2.7')

from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from config import *
import urllib2
import logging

class Core:

    def __init__(self):

        self.log = self.setup_logger()

        self._anki_browser = None
        self.thread_lock = threading.Lock()
        self.number_of_opening_tabs = 20
        self.max_number_of_opening_tabs = 100
        self.__mydriver = None
        self.proxy_flag = False
        self.download_thumbnail_image = True
        self.newList = []
        self.revList = []
        # hold notes that had bean opened or opening in tabs
        self.opening_tab_holder = {}
        # TODO
        # self.opening_tab_holder = {}

    def _open_many(self, browser):
        mw = browser.mw

        if self.max_number_of_opening_tabs > len(self.__mydriver.window_handles):
            
            # set limit of new/review queue to max_number_of_opening_tabs
            mw.col.sched.queueLimit = self.max_number_of_opening_tabs
            
            self.log.info('Executing _open_many() ...')

            if len(self.newList) == 0:
                self.newList = self.getAllNoteList(mw, list(mw.col.sched._newQueue))
                self.log.info('Got newList, length: [%d], newList: [%s]', len(self.newList), self.note_to_string(self.newList))
            if len(self.revList) == 0:
                self.revList = self.getAllNoteList(mw, list(mw.col.sched._revQueue))
                self.log.info('Got revList, length: [%d], revList: [%s]', len(self.revList), self.note_to_string(self.revList))

            needToOpenWindowsCount = self.max_number_of_opening_tabs - len(self.__mydriver.window_handles)

            if needToOpenWindowsCount % 2 == 0:
                half = needToOpenWindowsCount / 2
            else:
                half = needToOpenWindowsCount / 2 + 1

            for index in range(half):
                if len(self.newList) > 0:
                    thread.start_new_thread(self.__openUrlFromQueue, (self.newList.pop(), True))
                if len(self.revList) > 0:
                    thread.start_new_thread(self.__openUrlFromQueue, (self.revList.pop(), True))

    @staticmethod
    def note_to_string(note_list):
        words = {}
        for index in range(len(note_list)):
            note = note_list[index]
            words.__setitem__(index, note['Front'])

        return str(words.values())


    def getAllNoteList(self, mw, queue):
        noteList = []
        for index in range(len(queue)):
            card = mw.col.getCard(queue[index])
            note = mw.col.getNote(card.nid)
            if 'reminder' in note.keys():
                r = note['reminder']
                if r is None or unicode.strip(r) == '':
                    noteList.append(note)

        return noteList

    def doSearch(self, browser, note, how):
        import selenium
        import httplib

        try:
            self._anki_browser = browser
            self.__runFireFox()
            self. __setProxy4Urllib()
            # open one at first
            self.__openUrl(note)
            # open many
            self._open_many(browser)
            self.audit()
            self.__getImageInfo(note)
        except selenium.common.exceptions.SessionNotCreatedException:
            self.log.error('Failed to self.doSearch(), opening a new browser instance')
            import traceback
            self.log.error(traceback.format_exc())
            # reset opening_tab_holder
            self.opening_tab_holder = {}
            # reset global variable __mydriver
            self.__mydriver = None
            self.doSearch(browser, note, how)
        except selenium.common.exceptions.NoSuchWindowException:
            self.log.error('Opening url in a new tab')
            # try to switch a new tab then open url in this tab rather than open a new browser instance
            hs = self.__mydriver.window_handles
            self.__mydriver.switch_to.window(hs[0])
            self.doSearch(browser, note, how)
            self.del_existing_tab(self.__getCurrentPageTitle())
        except httplib.BadStatusLine as e:
            import traceback
            self.log.error(traceback.format_exc())
            self.doSearch(browser, note, how)
        except selenium.common.exceptions.WebDriverException as wde:
            self.log.error('selenium.common.exceptions.WebDriverException occurs, attempt to re-execute doSearch()')
            import traceback
            self.log.error(traceback.format_exc())
            self.doSearch(browser, note, how)
        except Exception as e:
            self.log.error('Error occurs when execute doSearch() ......')
            import traceback
            self.log.error(traceback.format_exc())

    def del_existing_tab(self, key):
        if key in self.opening_tab_holder.keys():
            del self.opening_tab_holder[key]

    def __runFireFox(self):
        if self.__mydriver is None:
            self.log.info('Opening browser')

            # set proxy for browser TODO
            profile = self.setProxy4Browser()

            options = webdriver.FirefoxOptions()
            # Open links in tabs instead of new windows
            options.set_preference('browser.link.open_newwindow', 3)
            # Open new tab but stay on the current tab
            options.set_preference('browser.tabs.loadDivertedInBackground', True)
            # allow 200 popup windows
            options.set_preference('dom.popup_maximum', 200)
            # always open new tabs at the end
            options.set_preference('browser.tabs.insertRelatedAfterCurrent', False)


            self.__mydriver = webdriver.Firefox(executable_path=executable_path,
                                         firefox_binary=firefox_binary,
                                         firefox_profile=profile,
                                         firefox_options=options)

            self.__mydriver.set_window_size(1302, 837)
            self.__mydriver.set_window_position(612, 33)


    def setProxy4Browser(self):
        if self.__proxyConfigExists():
            profile = webdriver.FirefoxProfile(firefox_profile)
            # # type -> Direct = 0, Manual = 1, PAC = 2, AUTODETECT = 4, SYSTEM = 5
            # profile.set_preference("network.proxy.type", 1)
            # # SOCKS4: 1 SOCKS5: 2 HTTP: 3
            # if protocol == 2 or protocol == 1:
            #     profile.set_preference("network.proxy.socks", server)
            #     profile.set_preference("network.proxy.socks_port", int(port))
            # elif protocol == 3:
            #     profile.set_preference("network.proxy.http", server)
            #     profile.set_preference("network.proxy.http_port", int(port))
            # profile.update_preferences()
        else:
            profile = firefox_profile
        return profile

    def __openUrlFromQueue(self, note, stayOnCurrentTab=False):
        import selenium
        try:
            word = unicode.strip(note['Front'])
            for key in self.opening_tab_holder.keys():
                if str(key).find(word) != -1:
                    self.log.info('The tab [%s] has bean opened for word [%s].', key, word)
                    return

            self.__openUrl(note, stayOnCurrentTab)
        except selenium.common.exceptions.SessionNotCreatedException as e:
            self.log.error('Failed to self.__openUrlFromQueue(), opening a new browser instance')
            import traceback
            self.log.error(traceback.format_exc())
            # reset opening_tab_holder
            self.opening_tab_holder = {}
            # reset global variable __mydriver
            self.__mydriver = None
            self.__runFireFox()
            self.__setProxy4Urllib()
            self.__openUrlFromQueue(note, stayOnCurrentTab)
        except selenium.common.exceptions.NoSuchWindowException as e:
            self.log.error('Opening url in the new tab')
            self.__openUrlFromQueue(note, True)
            self.del_existing_tab(self.__getCurrentPageTitle())
        except Exception:
            import traceback
            self.log.error(traceback.format_exc())
            self.__openUrlFromQueue(note, stayOnCurrentTab)

    def __getCurrentPageTitle(self, timeout=4):

        from selenium.webdriver.support import ui
        from selenium.common.exceptions import TimeoutException
        wait = ui.WebDriverWait(self.__mydriver,
                                timeout=timeout,
                                poll_frequency=0.25)
        title = ''
        try:
            # fast return
            ready_state = self.__mydriver.execute_script('return document.readyState')
            if ready_state == 'complete':
                href = self.__mydriver.execute_script('return window.location.href')
                if href == "about:blank":
                    return title

            # Wait until element '/html/head/title' is rendered
            wait.until(lambda browser: browser.find_element_by_xpath('/html/head/title'))
            title = self.__mydriver.title
        except TimeoutException: # ignore TimeoutException, return white space
            self.log.error("Raised TimeoutException")
            import traceback
            self.log.error(traceback.format_exc())
        # except NoSuchWindowException:
        #     del self.opening_tab_holder[self.__getCurrentPageTitle()]
        except Exception: # ignore other Exceptions, return white space
            self.log.error("Raised Exception")
            import traceback
            self.log.error(traceback.format_exc())

        self.log.info('The current page title is "%s"', title)

        return title

    def __switchToTab(self, word, lookup_tabs_from_the_end=False, wait_util_tab_is_opened=True, close_tab_if_blank=True):
        self.log.info('Executing __switchToTab() to [%s]...', word)

        curHandles = self.__mydriver.window_handles

        if len(curHandles) != len(self.opening_tab_holder):
            # reset
            self.opening_tab_holder.clear()

            if lookup_tabs_from_the_end:
                # if self.has_been_looked_all_opening_tabs is True:
                #     # lookup tabs from the last to the first, except those in self.opening_tab_holder
                #     curHandles = curHandles[:(len(self.opening_tab_holder) - 1):-1]
                # else:
                # lookup tabs from the last to the first
                curHandles = curHandles[::-1]

            for newHandle in curHandles:
                self.__mydriver.switch_to.window(newHandle)

                if wait_util_tab_is_opened:

                    # refresh current page
                    ready_state = self.__mydriver.execute_script('return document.readyState')
                    if ready_state == 'interactive':
                        if self.__getCurrentPageTitle(sys.maxsize) == "Problem loading page":
                            self.log.info('Refreshing the current tab due to %s and title "Problem loading page"', ready_state)
                            self.__mydriver.refresh()

                    title = self.__getCurrentPageTitle(sys.maxsize)

                    if title == '' or title is None:
                        # close the blank tab
                        if close_tab_if_blank:
                            # If close the last tab, the whole browser will be closed
                            if len(self.__mydriver.window_handles) > 1:
                                self.closeTab(newHandle, title)
                                continue

                        # refresh current page
                        # ready_state = self.__mydriver.execute_script('return document.readyState')
                        # if ready_state == 'uninitialized':
                        #     self.log.info('Refreshing the current tab due to %s ', ready_state)
                        #     self.__mydriver.refresh()

                if (title != '' and title is not None) and title not in self.opening_tab_holder:
                    self.log.info('Saving tab [%s], title is [%s]', newHandle, title)
                    # save title and current window_handle
                    self.opening_tab_holder.__setitem__(title, newHandle)
                else:
                    # close the duplicated window
                    if close_tab_if_blank:
                        # If close the last tab, the whole browser will be closed
                        if len(self.__mydriver.window_handles) > 1:
                            # Should not close the saved tab
                            if newHandle != self.opening_tab_holder[title]:
                                self.closeTab(newHandle, title)

            self.log.info("The size of self.opening_tab_holder is [%d]", len(self.opening_tab_holder))

        # check tab saved
        if self.__switchToWindowSaved(word):
            return True

        return False

    def closeTab(self, newHandle, title):
        self.log.info("Closing the tab [%s], it's title is [%s]" % (newHandle, title))
        try:
            self.__mydriver.close()
        except Exception:
            self.log.error("Failed to close the tab [%s], it's title is [%s]" % (newHandle, title))
            import traceback
            self.log.error(traceback.format_exc())
            pass

    def __switchToWindowSaved(self, word):
        self.log.info('Switching to a saved tab, opening_tab_holder: [%s]', str(self.opening_tab_holder))

        for savedTabTitle in self.opening_tab_holder.keys():
            if savedTabTitle.find(word) != -1:
                savedWindowhandle = self.opening_tab_holder[savedTabTitle]
                import selenium
                try:
                    self.__mydriver.switch_to.window(savedWindowhandle)
                    self.log.info('Switched to the saved tab "%s"', savedTabTitle)
                    self.del_existing_tab(savedTabTitle)
                    self.log.info('Deleted the saved tab "%s" after switching tab "%s"', savedTabTitle, savedWindowhandle)
                    return True
                except selenium.common.exceptions.NoSuchWindowException:
                    self.del_existing_tab(savedTabTitle)
                    self.log.error('Deleted the saved tab "%s" because of no such tab "%s"', savedTabTitle, savedWindowhandle)
                    return False
        return False

    def __openUrl(self, note, stayOnCurrentTab=False):
        word = unicode.strip(note['Front'])
        url = ddg_searchimage_url % word

        self.log.info('Opening ' + url)

        if stayOnCurrentTab is False:

            if len(self.__mydriver.window_handles) < self.max_number_of_opening_tabs \
                    and self.__switchToTab(word, False):
                return

            # self.__mydriver.get(url)

            self.__mydriver.execute_script('window.open("%s")' % url)
            self.log.info('Opened %s', url)
            self.__switchToTab(word, True, True, False)
        else:
            try:

                self.__mydriver.execute_script('window.open("%s")' % url)

            except Exception:
                # catch exception for now to avoid to open duplicate tabs
                self.log.error('Exception occurs when opening [%]', url)
                import traceback
                self.log.error(traceback.format_exc())

    # TODO
    def __doWhithinThread(self, ):
        thread.start_new_thread(self.doSearch)


    def __getTitle(self, reallyUrlOfArticle, retryTimes = 2):
        self.log.info('Getting title from [%s]', reallyUrlOfArticle)
        if retryTimes <= 0:
            return ''
        from httplib import IncompleteRead
        try:
            html = self.getResponse(reallyUrlOfArticle, 6).read()
            content = etree.HTML(html)
            src = content.xpath(title_xpath)
            if len(src) > 0:
                title = src[0].text
                self.log.info('Got title [%s]', title)
                return title
            return ''
        except socket.timeout as e:
            # if timeout try again and again until success.(Or maybe I should change a better proxy or ISP:))
            self.log.error('Timeout. Try again... ')
            return self.__getTitle(reallyUrlOfArticle, retryTimes - 1)
        except IncompleteRead as ir:
            self.log.error('Try again, cause: [%s]', str(ir.message))
            return self.__getTitle(reallyUrlOfArticle, retryTimes - 1)
        except Exception:
            import traceback
            self.log.error(traceback.format_exc())
            # don't attempt to get title from origin page source
            return ''

    # set default retrytimes = 2
    def __downloadImage(self, href, thumbnailUrl, fileName, retryTimes=2):
        # download in a thread
        thread.start_new_thread(self._download, (href, thumbnailUrl, fileName, retryTimes))

    # set default retrytimes = 2
    def _download(self, href, thumbnailUrl, fileName, retryTimes=2):
        import urllib2
        import httplib
        success = False
        while success is False:
            try:
                try:
                    filepath = self.buildFilePath(fileName)

                    if self.download_thumbnail_image:
                        href = thumbnailUrl

                    self.log.info('downloading %s to %s', href, filepath)
                    response = self.getResponse(href)
                    data = response.read()

                    out_file = open(filepath, 'wb')
                    out_file.write(data)
                    self.log.info('downloaded %s to %s', href, filepath)
                    success = True
                except (urllib2.HTTPError, urllib2.URLError) as he:
                    import traceback
                    self.log.error(traceback.format_exc())
                    href = thumbnailUrl
                except socket.timeout:
                    self.log.error('retryTimes [%s]', str(retryTimes))
                    retryTimes = retryTimes - 1
                    if retryTimes <= 0:
                        self.log.error('Time out when opening the original link, attempt to download the thumbnail image ...')
                        href = thumbnailUrl
                except httplib.IncompleteRead as ir:
                    import traceback
                    self.log.error(traceback.format_exc())
                except Exception:
                    import traceback
                    self.log.error(traceback.format_exc())
                    href = thumbnailUrl
            except Exception:
                import traceback
                self.log.error(traceback.format_exc())
                success = True

    def __proxyConfigExists(self):
        return protocol in [1, 2, 3] and len(server) > 0 and len(port) > 0

    def __setProxy4Urllib(self):

        if self.proxy_flag is False and self.__proxyConfigExists():
            # set proxy for urllib2
            self.log.info('setting proxy %s %s:%s', protocol, server, port)
            from sockshandler import SocksiPyHandler
            global proxy
            proxy = SocksiPyHandler(protocol, server, int(port))
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)
            self.proxy_flag = True
        else:
            self.log.info('Proxy has bean configured: protocol=%d server=%s port=%s', protocol, server, port)

    def __unSetProxy(self):
        if self.proxy_flag is True and self.__proxyConfigExists:
            self.proxy_flag = False
            handlers = urllib2._opener.handlers
            copyOpners = []
            for handler in handlers:
                # filter to drop proxy
                if handler != proxy:
                    opener = urllib2.build_opener(handler)
                    copyOpners.append(opener)
                else:
                    self.log.info('un-setting proxy %s %s:%s', protocol, server, port)

            # fill new opener into uillib2
            for opener in copyOpners:
                urllib2.install_opener(opener)

    def getResponse(self, url, timeout=30):
        # set user-agent to fix http 403 error
        userAngent = 'Mozilla/5.0 (X11; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0'
        req = urllib2.Request(url, headers={'User-Agent': userAngent})
        response = urllib2.urlopen(req, timeout=timeout)
        return response


    def buildFilePath(self, fileName):
        ankiCollectionMediaFilePath = os.path.join(self._anki_browser.mw.pm.profileFolder(), "collection.media") + '/' + fileName
        return ankiCollectionMediaFilePath


    def fillTemplete(self, imageFileName, heading, articleUrl):
        image = '<img src="%s" />' % imageFileName
        heading = '<div>%s</div>' % heading
        articleUrl = '<div><a href="%s">link</a></div>' % (articleUrl)

        return image + heading + articleUrl


    def __getImageInfo(self, note):

        content, write2Disk = self.__main_loop(note)

        if write2Disk:
            # save note
            content = note[image_field_name] + content
            self.log.info('Saving note [%s]', content)
            note[image_field_name] = content
            note.flush()

        self.log.info('done')

    # def __doGetImageInfoWithinThread(note):
    #     thread.start_new_thread(__doGetImageInfo, (note, ))

    def getFileName(self, reallyUrlImage, ht, word):
        import hashlib
        md5 = hashlib.md5(str(reallyUrlImage + ht)).hexdigest()
        postfix = reallyUrlImage.split('.')[::-1][0]
        # eg.
        # https://qph.ec.quoracdn.net/main-qimg-e03132b7fa96565a036c77facf91d752
        # and
        # images.duckduckgo.com/iu/?u=https://tse2.mm.bing.net/th?id=OIP.RaRTW9MRgpU8Wbgu35dXigHaJl&pid=15.1&amp;f=1
        # has a unknown postfix
        # actually the first file type is png
        # but I think a postfix is no matter at all
        # software should recognize
        if len(postfix) > 3:
            postfix = 'jpg'
        return word + '_' + md5 + '.' + postfix

    def __main_loop(self, note):
        word = unicode.strip(note['Front'])
        content = ''
        write2Disk = False
        while 1:

            import selenium
            import httplib
            from httplib import ResponseNotReady
            try:

                if self._element_exist_by_xpath(ddg_heading_xpath) is False:
                    continue

                # Do this job in a thread
                thread.start_new_thread(self._insert_input_into_page_source, ('imagepicker_identity_id',))

                is_selected = self._is_selected_by_id('imagepicker_identity_id')
                if is_selected is False:
                    continue

                heading = self.__mydriver.find_element_by_xpath(ddg_heading_xpath)
                self.log.info('Got heading [%s] ' + str(heading.text))

                ht = str(heading.text)
                # really url of article
                reallyUrlOfArticle = heading.get_attribute('href')
                self.log.info('Got really url of article [%s]', reallyUrlOfArticle)

                # really url of image
                image = self.__mydriver.find_element_by_xpath(ddg_image_xpath)
                reallyUrlImage = image.get_attribute('href')
                self.log.info('Got really url of image [%s]', reallyUrlImage)

                ddgImageThumbnailUrl = self.__mydriver.find_element_by_xpath(ddg_image_thumbnail_xpath).get_attribute('src')
                self.log.info('Got image thumbnail url [%s]', ddgImageThumbnailUrl)

                # Now we can close the slider
                self.closeTheSlider()

                self.log.info('The original content of image field is [%s]', str(note[image_field_name]))
                # avoid duplication
                if str(note[image_field_name]).find(reallyUrlOfArticle) == -1 and content.find(reallyUrlOfArticle) == -1:

                    import os

                    imageFileName = self.getFileName(reallyUrlImage, ht, word)
                    self.log.info('The name of image file is [%s]', imageFileName)

                    self.__downloadImage(reallyUrlImage, ddgImageThumbnailUrl, imageFileName, 1)

                    # need to get complete title from origin article
                    if ht.endswith('...'):
                        # not youtube
                        # spent too long time to fetch the heading from youtube.com
                        # but only return 'YouTube'
                        if reallyUrlOfArticle.find('youtube.com') == -1:
                            title = self.__getTitle(reallyUrlOfArticle)
                            if len(title) == 0:
                                # Use ddg's title
                                title = ht
                    else:
                        title = ht
                    self.log.info('Using title [%s]', title)

                    content = content + self.fillTemplete(imageFileName, title, reallyUrlOfArticle)

                    write2Disk = True

                    self.__setProxy4Urllib()
                else:
                    self.log.info("This picture and it's information has bean added ...")

            except selenium.common.exceptions.NoSuchElementException as e:
                # just ignore if we cannot find element
                pass;
            except (httplib.BadStatusLine,
                    urllib2.URLError,
                    AttributeError,
                    ResponseNotReady,
                    httplib.CannotSendRequest):
                # log exception
                import traceback
                self.log.error(traceback.format_exc())
            except urllib2.HTTPError as he:
                import traceback
                self.log.error(traceback.format_exc())
                if he.code == 502:
                    self.log.error('HTTP Code: 502. Maybe the page is currently offline, please choose other image')
                elif he.code == 605:
                    # Attempt to remove proxy to fix this issue
                    self.log.error('HTTP Code: 605. Attempting to remove proxy to fix this issue')
                    self.__unSetProxy()
            except selenium.common.exceptions.NoSuchWindowException:
                self.log.info("Quiting the main loop")
                break
            except Exception:
                import traceback
                self.log.error(traceback.format_exc())
                break

        return content, write2Disk

    def _insert_input_into_page_source(self, imagepicker_identity_id):
        try:
            with self.thread_lock:
                if self._element_exist_by_id(imagepicker_identity_id) is False:
                    # insert <a>...</a> into page source
                    tag_check_box = "<input id=\"imagepicker_identity_id\" type=\"checkbox\"/>"
                    tag_a = self.__mydriver.find_element_by_xpath(ddg_heading_xpath) \
                        .find_element_by_xpath("..")
                    self.__mydriver.execute_script("var ele=arguments[0]; ele.innerHTML = '%s';"
                                                       % (tag_a.get_attribute('innerHTML') + tag_check_box), tag_a)
        except:
            import traceback
            self.log.error(traceback.format_exc())

    # close the slider
    def closeTheSlider(self):
        from selenium.common.exceptions import ElementClickInterceptedException
        try:
            self.__mydriver.find_element_by_xpath(ddg_image_detail_slider_xpath).click()
        except ElementClickInterceptedException as e:
            # Can not close this slider automatically. But We have noted this image and it's infomation, so we can be free to focus other images.
            self.log.error('Can not close this slider automatically. Please close the slider by yourself.')

    def audit(self):
        self.log.info('The number of windows is %s at the moment', len(self.__mydriver.window_handles))

    def setup_logger(self, filename='image-picker.log'):
        log = logging.getLogger(__name__)

        logging.basicConfig(filename=filename,
                            level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(threadName)s -  %(levelname)s - %(message)s')

        return log

    def _element_exist_by_id(self, id):
        try:
            self.__mydriver.find_element_by_id(id)
            return True
        except:
            return False

    def _element_exist_by_xpath(self, xpath):
        self.__mydriver.find_element_by_xpath(xpath)
        return True

    def _is_selected_by_id(self, id):
        try:
            return self.__mydriver.find_element_by_id(id).is_selected()
        except StaleElementReferenceException:
            return False
