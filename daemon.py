"""
Disk And Execution MONitor (Daemon)

Configurable daemon behaviors:

  1.) The current working directory set to the "/" directory.
  2.) The current file creation mode mask set to 0.
  3.) Close all open files.
  4.) Redirect standard I/O streams to "/dev/null".

Based on an implementation by Chad J. Schroeder
"""

import os
import resource

# Notes
# ========
# os._exit() vs. os.exit()
#   _exit, unlike exit(), does not call any atexit hooks or signal handlers. 
#   Using exit() may cause all stdio streams to be flushed twice and any
#   temporary files may be unexpectedly removed. 


def daemonize(workdir='/', redirect_to=os.devnull, umask=0):
    """
    Detach a process from the controlling terminal and run it in the
    background as a daemon.

    redirect_to:
      Redirect standard I/O file descriptors to the specified file
      (by default, /dev/null).

      Since the daemon has no controlling terminal, most daemons redirect 
      stdin, stdout, and stderr to /dev/null. This is done to prevent
      side-effects from reads and writes to the standard I/O file descriptors.

      Passing workdir=None will leave the process in it's current directory

    workdir:
      Default working directory for the daemon.

      Since the current working directory may be a mounted filesystem, we
      avoid the issue of not being able to unmount the filesystem at
      shutdown time by changing it to the root directory (by default).

    umask:
      File mode creation mask of the daemon.    

    Note:
      * This function will close all open file descriptors. If you processes
        reads/writes to any files, it must call daemonize before opening them.
    """

    # Fork a child process so the parent can exit.  
    # * returns control to the command-line or shell. 
    # * guarantees child will not be a process group leader, since the child 
    #   receives a new process ID and inherits the parent's process group ID.
    # * required to insure that the next call to os.setsid is successful.
    pid = os.fork()

    if pid == 0:	# The first child.
        # To become the session leader of this new session and the process group
        # leader of the new process group, we call os.setsid().  The process is
        # also guaranteed not to have a controlling terminal.
        os.setsid()

        # Fork a second child
        # ===================
        # Fork a second child and exit immediately to prevent zombies. This
        # causes the second child process to be orphaned, making the init
        # process responsible for its cleanup.  And, since the first child is
        # a session leader without a controlling terminal, it's possible for
        # it to acquire one by opening a terminal in the future (System V-
        # based systems).  This second fork guarantees that the child is no
        # longer a session leader, preventing the daemon from ever acquiring
        # a controlling terminal.
        pid = os.fork()

        if pid == 0:	# The second child.

            # Since the current working directory may be a mounted filesystem, we
            # avoid the issue of not being able to unmount the filesystem at
            # shutdown time by changing it to the root directory.
            if workdir is not None:
                os.chdir(workdir)

            # We probably don't want the file mode creation mask inherited from
            # the parent, so we give the child complete control over permissions.
            os.umask(umask)

        else:
            # Exit parent (the first child) of the second child.
            os._exit(0)
    else:
        os._exit(0)	# Exit parent of the first child.


    # Close all open file descriptors.  This prevents the child from keeping
    # open any file descriptors inherited from the parent.
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        # Default maximum for the number of available file descriptors.
        maxfd = 1024

    # close all file descriptors.
    for fd in xrange(maxfd):
        try:
            os.close(fd)
        except OSError:	# ERROR, fd wasn't open to begin with (ignored)
            pass
    
    # Redirect the standard I/O file descriptors to the specified file.  Since
    # the daemon has no controlling terminal, most daemons redirect stdin,
    # stdout, and stderr to /dev/null.  This is done to prevent side-effects
    # from reads and writes to the standard I/O file descriptors.

    # This call to open is guaranteed to return the lowest file descriptor,
    # which will be 0 (stdin), since it was closed above.
    os.open(redirect_to, os.O_RDWR|os.O_CREAT)  # standard input (0)

    # Duplicate standard input to standard output and standard error.
    os.dup2(0, 1)    # standard output (1)
    os.dup2(0, 2)    # standard error (2)


if __name__ == "__main__":

    from textwrap import dedent
    print 'pid:', os.getpid()

    daemonize(None, 'daemon.out')

    # daemon can still write to files
    with file("daemon.info", "wb") as f:
        f.write(dedent("""\
        process ID         = %s
        parent process ID  = %s
        process group ID   = %s
        session ID         = %s
        user ID            = %s
        effective user ID  = %s
        real group ID      = %s
        effective group ID = %s
        """ % (os.getpid(), os.getppid(), os.getpgrp(), os.getsid(0),
               os.getuid(), os.geteuid(), os.getgid(), os.getegid())))
        f.write('\n')

    print "Hello I'm a daemon and this is my standard out."


