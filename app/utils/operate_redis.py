import redis
import re
from config import Config
r = redis.StrictRedis(host=Config.REDIS_SERVER, port=6379, db=0, password=Config.REDIS_KEY)

class MRedis:
    def __init__(self, siteId = 1):
        self.siteId = siteId

    def keepRequest(self):
        '''
        从服务器向主服务器发起请求，获取任务Url
        '''
        items = r.brpop("spider.wait", 120)
        if items is not None:
            return items[1].decode()
        else:
            return None

    
    def exist(self, requestUrl):
        """
        判断是否存在
        """
        return r.sismember("spider.all", requestUrl)

    def isValidKey(self, key):
        """
        判断HASH是否存在
        """
        isExists = r.exists(key)
        if isExists:
            item = r.hgetall(key)
        if isExists and item:
            return True
        else:
            return False

    def addRequest(self, requestUrl):
        """
        spider.all   set集合，包含所有请求（已处理，未处理。）
        spider.wait  list    待处理请求
        """
        if not r.sismember("spider.all", requestUrl):
            pipe = r.pipeline()
            pipe.sadd("spider.all", requestUrl)
            pipe.lpush("spider.wait", requestUrl)
            pipe.execute()

    def checkFinish(self):
        """
        检查书籍是否已被完整抓取
        """
        book_keys = r.keys("%s_book_*" % (self.siteId))
        pattern = re.compile(r'[\s\_]+')
        if not book_keys:
            return
        for book_key in book_keys:
            bookId = re.split(pattern, book_key.decode())[2]
            chapters = r.keys("%s_chapter_%s_*" % (self.siteId, bookId))
            contents = r.keys("%s_content_%s_*" % (self.siteId, bookId))
            chapter_count = len(chapters)
            content_count = len(contents)

            if chapter_count == 0:
                #r.lpush("spider.wait", "https://book.qidian.com/info/%s" %  bookId)
                continue
            if chapter_count - content_count < 10:
                key = "%s_book_%s" % (self.siteId, bookId)
                if not r.sismember("save.all", key):
                    pipe = r.pipeline()
                    pipe.sadd("save.all", key)
                    pipe.lpush("save.wait", key)
                    pipe.execute()
            else:
                print("%s %s %s" % (bookId, chapter_count, content_count))

    def addSpiderError(self, requestUrl):
        """
        set
        请求出错集合
        """
        r.sadd("error.spider", requestUrl)

    def addSaveError(self, value):
        """
        set
        保存出错集合
        """
        r.sadd("error.save", value)


    def setBookHash(self, mapping):
        """
        HASH 哈希表
        key ：siteId_book_xbookId
        """
        r.hmset('%s_book_%s' % (self.siteId, mapping['xbookId']), mapping)

    def setChapterHash(self, mapping):
        """
        HASH 哈希表
        key ：siteId_chapter_xbookId_xchapterId
        """
        r.hmset('%s_chapter_%s_%s' % (self.siteId, mapping['xbookId'], mapping['xchapterId']), mapping)

    def setContentHash(self, mapping):
        """
        HASH 哈希表
        key: siteId_content_xbookId_xchapterId
        """
        r.hmset('%s_content_%s_%s' % (self.siteId, mapping['xbookId'], mapping['xchapterId']), mapping)

    def getBookHash(self, id):
        key = "%s_book_%s" % (self.siteId, id)
        mHash = r.hgetall(key)
        book = dict()
        for key in mHash:
            book[key.decode()] = mHash[key].decode()

    def getBook(self):
        """
        从Redis中取出book数据
        """
        items = r.brpop("save.wait", 120)
        if not items:
            return None
        key = items[1].decode()
        mHash = r.hgetall(key)
        book = dict()
        for key in mHash:
            book[key.decode()] = mHash[key].decode()
        return book

    def getChapterList(self, bookId):
        """
        从Redis中取出[chapter]数据
        """
        chapterList = []
        keys = r.keys("%s_chapter_%s_*" % (self.siteId, bookId))
        for k in keys:
            key = k.decode()
            mHash = r.hgetall(key)
            chapter = dict()
            for key in mHash:
                chapter[key.decode()] = mHash[key].decode()
            if 'xchapterId' in chapter.keys():
                chapterList.append(chapter)
        return chapterList

    def getContent(self, bookId, chapterId):
        """
        从Redis中取出[chapter]数据
        """
        key = "%s_content_%s_%s" % (self.siteId, bookId, chapterId)
        mHash = r.hgetall(key)
        content = dict()
        for key in mHash:
            content[key.decode()] = mHash[key].decode()
        return content