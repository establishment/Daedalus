import os
import time
import errno


class FileLockException(Exception):
    pass


class FileLock(object):
    filelock_dir_path = os.getcwd()

    @classmethod
    def set_filelock_dir(cls, filelock_dir):
        cls.filelock_dir_path = filelock_dir

    def __init__(self, file_name, session_uid=None, timeout=10, delay=.05):
        self.is_locked = False
        self.lockfile = os.path.join(FileLock.filelock_dir_path, "%s.lock" % file_name)
        self.file_name = file_name
        self.timeout = timeout
        self.delay = delay
        self.session_uid = session_uid
        self.is_owner = False

        self.fd = None

    def trylock(self):
        if not self.is_locked:
            try:
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                self.is_owner = True
                self.is_locked = True
                os.write(self.fd, str.encode(self.session_uid))
            except OSError as e:
                if e.errno == errno.EEXIST:
                    with open(self.lockfile, "r") as f:
                        current_session_uid = f.read()
                        if current_session_uid == self.session_uid:
                            self.is_owner = False
                            self.is_locked = True
        return self.is_locked

    def acquire(self):
        start_time = time.time()
        while True:
            if self.trylock():
                break
            if (time.time() - start_time) >= self.timeout:
                raise FileLockException("Timeout occurred.")
            time.sleep(self.delay)

    def got_ownership(self):
        if not self.is_owner:
            return False
        if not self.is_locked:
            return False
        with open(self.lockfile, "r") as f:
            current_session_uid = f.read()
            if current_session_uid == self.session_uid:
                return True
        return False

    def release(self, force=False):
        if self.got_ownership():
            os.close(self.fd)
            os.unlink(self.lockfile)
        elif force:
            os.unlink(self.lockfile)
        self.is_locked = False
        self.is_owner = False
