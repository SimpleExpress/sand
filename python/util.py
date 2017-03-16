# coding=utf-8

import os
import six
import logging
import smtplib
import subprocess
import mimetypes

from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from functools import partial


def T(v, null_literal='None', encoding='utf-8'):
    if v is None:
        v = null_literal

    if issubclass(type(v), six.text_type):  # unicode(2), str(3)
            s = v
    else:
        try:
            # basestring(2), str(2), bytes(3) -> text
            base_types = (six.binary_type, six.string_types)
            if issubclass(type(v), base_types):
                s = v.decode(encoding)
            else:  # object -> text
                s = six.text_type(v)
        except UnicodeDecodeError:
            logging.error('cannot convert to string: %s' % v)
            s = None
    return s


def send_mail(mail_config, subject, mail_list, content, *files):

    def make_attachment(path):
        ctype, encoding = mimetypes.guess_type(path)
        if ctype:
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'text':
                mime_cls = partial(MIMEText,
                                   _charset=encoding if encoding else 'utf-8')
            elif maintype == 'image':
                mime_cls = MIMEImage
            elif maintype == 'audio':
                mime_cls = MIMEAudio
            else:
                mime_cls = partial(MIMEBase, maintype, subtype)
        else:
            mime_cls = partial(MIMEText,
                               _charset=encoding if encoding else 'utf-8')
            subtype = 'plain'

        with open(path, 'rb') as fh:
            if mime_cls == MIMEBase or \
                    getattr(mime_cls, 'func', None) == MIMEBase:
                attachment = mime_cls()
                attachment.set_payload(fh.read())
                encoders.encode_base64(attachment)
            else:
                attachment = mime_cls(fh.read(), _subtype=subtype)

        attachment.add_header('Content-Disposition',
                              'attachment',
                              filename=os.path.basename(path))
        return attachment

    try:
        message = MIMEMultipart()
        _subtype = 'html' if '</html>' in content else 'plain'
        message.attach(MIMEText(content, _subtype, 'utf-8'))
        message["Subject"] = subject
        message["From"] = mail_config['user']
        message["To"] = ";".join(mail_list)
        for f in files:
            if os.path.exists(f):
                message.attach(make_attachment(f))

        client = smtplib.SMTP()
        client.connect(mail_config['host'], mail_config['port'])
        if mail_config.get('use-ssl', False):
            client.starttls()
        client.login(mail_config['user'], mail_config['password'])
        client.sendmail(mail_config['user'],
                        mail_list,
                        message.as_string())
        client.quit()
    except:
        logging.exception('error in sending email')
        raise


def shell(cmd, ignore_output=True):
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    logging.info('%s -> %s' % (cmd, p.returncode))

    if ignore_output:
        if out:
            logging.debug(out)
        if err:
            logging.error(err)
        return p.returncode
    else:
        return p.returncode, out, err


def stream(paths, func_accept_file=None):
    def default_accept(container_path, name):
        return name

    if not func_accept_file:
        func_accept_file = default_accept

    files = []
    if not isinstance(paths, (tuple, list)):
        paths = [paths, ]
    for path in paths:
        if os.path.isfile(path):
            files.append(path)
        else:
            all_files = os.listdir(path)
            for f in all_files:
                if func_accept_file(path, f):
                    files.append(os.path.join(path, f))

    for path in files:
        try:
            logging.debug('reading file: %s' % path)
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        yield line
        except OSError as e:
            logging.error("error in reading file %s: %s" % (path, e))
