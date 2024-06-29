#
#  Copyright (C) 2021 GENG YUN Technology Pte. Ltd.
#  All rights reserved.
#
#  NOTICE: All information contained herein is, and remains the
#  property of GENG YUN Technology Pte. Ltd. and its suppliers, if
#  any. The intellectual and technical concepts contained herein are
#  proprietary to GENG YUN Technology Pte. Ltd. and are protected by
#  patent or trade secret or copyright law.
#
#  Dissemination of this information or reproduction of this material
#  is strictly forbidden unless prior written permission is obtained
#  from GENG YUN Technology Pte. Ltd.
#
#  Distribution of source code or binaries derived from this file is
#  not permitted. You should have received a copy of the End User
#  License Agreement along with this program; if not, please contact
#  GENG YUN Technology Pte. Ltd. <sales@pynv.me>

# -*- coding: utf-8 -*-

import logging
import nvme as d

class Namespace():
    def __init__(self, nvme0, size, cap=None, flbas=1):
        if cap == None:
            cap = size

        self.nvme0 = nvme0
        
        logging.debug(size)
        buf = d.Buffer()
        buf[0:7] = size.to_bytes(8, "little")
        buf[8:15] = cap.to_bytes(8, "little")
        buf[26] = flbas
        
        error = 0
        def _cb(cpl):
            nonlocal error
            logging.debug(cpl)
            error = (cpl[3]>>17)&0x3ff
        logging.info("Create new ns - size:{} blocks, flba:{}".format(size, flbas))
        self._nsid = nvme0.send_cmd(0x0d, buf, nsid=0, cdw10=0, cb=_cb).waitdone()  # ns create
        # Do not initialize namespace here so that we can control each step at test scripts.
        # For example, skip ns creation and attach flow easily if necessary.
         
    def delete(self):
        self.nvme0.send_cmd(0x0d, nsid=self._nsid, cdw10=1).waitdone() # ns delete
        self.nvme0.getfeatures(7).waitdone() # ns delete

    @staticmethod
    def delete_all(nvme0):
        nvme0.send_cmd(0x0d, nsid=0xffffffff, cdw10=1).waitdone()
        nvme0.getfeatures(7).waitdone() # delete_all

    def attach(self, *cntlid_list):
        buf = d.Buffer()
        count = len(cntlid_list)
        buf[0:1] = count.to_bytes(2, "little")
        for i in range(count):
            buf[2+2*i:3+2*i] = cntlid_list[i].to_bytes(2, "little")
        # logging.debug(buf.dump(16))
        logging.info("Attach ns(id:{}) to ctrl(id:{})".format(self._nsid, cntlid_list))
        return self.nvme0.send_cmd(0x15, buf, nsid=self._nsid, cdw10=0).waitdone()  # ns attach

    def detach(self, *cntlid_list):
        buf = d.Buffer()
        count = len(cntlid_list)
        buf[0:1] = count.to_bytes(2, "little")
        for i in range(count):
            buf[2+2*i:3+2*i] = cntlid_list[i].to_bytes(2, "little")
        # logging.debug(buf.dump(16))
        return self.nvme0.send_cmd(0x15, buf, nsid=self._nsid, cdw10=1).waitdone() # ns detach
    
