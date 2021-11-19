from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import switch_ofp1_3_mod

import time
import sys

class LinkProbe(switch_ofp1_3_mod.Switch):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LinkProbe, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self.Periodic_Stats)
        #
        self.ICMPReq = {}     #The number of ICMP Request packet from the begining
        self.ICMPRep = {}     #The number of ICMP Reply   packet from the begining
        #
        self.ICMPReq60 = {}     #The number of ICMP Request packet in last 60 seconds
        self.ICMPRep60 = {}     #The number of ICMP Reply   packet in last 60 seconds
        self.IsUpdate  = False

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def StateChange(self, ev):
        dp          = ev.datapath
        swid        = dp.id
        print ("StateChange  -  dpid={}".format(swid))

        if ev.state == MAIN_DISPATCHER:
            self.datapaths.setdefault(swid,dp)
            #
            self.ICMPReq.setdefault(swid,[])
            self.ICMPRep.setdefault(swid,[])

        if ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(swid)
            #
            self.ICMPReq.pop(swid)
            self.ICMPRep.pop(swid)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def FlowStatsReply(self, ev):
        msg  = ev.msg
        body = msg.body
        dp   = msg.datapath
        dpid = dp.id

        #Clear ICMPReq60 and ICMPRep60 after estimating the link loss
        if self.IsUpdate == False:
            self.ICMPReq60.clear()
            self.ICMPRep60.clear()
            self.IsUpdate = True
            
        icmp = [flow for flow in body if flow.match['ip_proto'] == 1]
        
        for stat in icmp:
            if stat.match['ipv4_src']=="10.0.0.1" and stat.match['ipv4_dst']=="10.0.0.4":
                if stat.match['icmpv4_type'] == 8: #ICMP request]
                    self.ICMPReq[dpid].append(stat.packet_count)
                    #
                    _len = len(self.ICMPReq[dpid])
                    if _len > 1:
                        self.ICMPReq60[dpid] = self.ICMPReq[dpid][_len-1] - self.ICMPReq[dpid][_len-2]
                    else:
                        self.ICMPReq60[dpid] = self.ICMPReq[dpid][0]

            if stat.match['ipv4_src']=="10.0.0.4" and stat.match['ipv4_dst']=="10.0.0.1":
                if stat.match['icmpv4_type'] == 0: #ICMP reply
                    self.ICMPRep[dpid].append(stat.packet_count)
                    #
                    _len = len(self.ICMPRep[dpid])
                    if _len > 1:
                        self.ICMPRep60[dpid] = self.ICMPRep[dpid][_len-1] - self.ICMPRep[dpid][_len-2]
                    else:
                        self.ICMPRep60[dpid] = self.ICMPRep[dpid][0]

        self.EstimateLinkLoss()
    

    def EstimateLinkLoss(self):
        if len(self.ICMPRep60.keys()) < len(self.datapaths.keys()):
            #Not receive enough data from all OFSs
            return

        self.IsUpdate = False

        print("\nNo. ICMP Request = {}   -   No. ICMP Reply = {}".format(self.ICMPReq60,self.ICMPRep60,))

        ###################################
        dpid_sort = sorted(self.datapaths.keys())
        for i in range(len(dpid_sort)-1):
            _dpid1 = dpid_sort[i]
            _dpid2 = dpid_sort[i+1]

            link_loss = float(self.ICMPReq60[_dpid1] - self.ICMPReq60[_dpid2])/self.ICMPReq60[_dpid1]
            print ("Link {} to {}: r={}".format(_dpid1,_dpid2,link_loss))
        
        ###################################
        dpid_sort = sorted(self.datapaths.keys(), reverse=True)
        for i in range(len(dpid_sort)-1):
            _dpid1 = dpid_sort[i]
            _dpid2 = dpid_sort[i+1]

            link_loss = float(self.ICMPRep60[_dpid1] - self.ICMPRep60[_dpid2])/self.ICMPRep60[_dpid1]
            print ("Link {} to {}: r={}".format(_dpid1,_dpid2,link_loss))
        

    def Periodic_Stats(self):
        while 1:
            self.ShowWaitingTime(60)

            for dp in self.datapaths.values():
                ofp_parser    = dp.ofproto_parser
                match = ofp_parser.OFPMatch(eth_type=0x800, ip_proto=1)
                FlowStats_req = ofp_parser.OFPFlowStatsRequest(dp, match=match)
                dp.send_msg(FlowStats_req)
            
    
    def ShowWaitingTime(self,sec):
        for remaining in range(sec, 0, -1):
            hub.sleep(1)
            sys.stdout.write("\r")
            _str = ["=" for sp in range(10-(remaining+9)%10)]
            sys.stdout.write("{:2d} seconds remaining {}>          ".format(remaining, "".join(_str)))
            sys.stdout.flush()