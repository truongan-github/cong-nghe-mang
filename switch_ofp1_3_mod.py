from _typeshed import IdentityFunction
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet, ethernet, ipv4, icmpv6, arp, lldp
import datetime

class Switch(app_manager.RyuApp):
    OFP_VERSIONS =[ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Switch, self).__init__(*args, **kwargs)
        self.MAC_table = {}

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp  = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        pin  = msg.match['in_port']
        swid = dp.id

        pkt = packet.Packet(msg.data)

        #Ethernet
        etherh = pkt.get_protocol(ethernet.ethernet)
        smac = etherh.src
        dmac = etherh.dst
        pin = msg.match['in_port']
        pout = 0
        dpid = dp.id

        #IPv4
        ipv4h = pkt.get_protocol(ipv4.ipv4)
        if ipv4h:
            sipv4 = ipv4h.src
            dipv4 = ipv4h.dst
            proto = ipv4h.proto

        #ICMP
        if pkt.get_protocol(lldp.lldp) or pkt.get_protocol(icmpv6.icmpv6):
            return

        print("\OFC receives Packet-In messeage from Datapath ID of {} --- Log at: {}".format(dpid,datetime.datetime.now()))

        self.MAC_table.setdefault(dpid,{})
        if (self.MAC_table[dpid].get(smac) != pin):
            self.MAC_table[dpid][smac] = pin
            print("    -Updates MAC table: MAC={} <-> Port-{}".format(smac,pin))


        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            _sip = arp_pkt.src_ip
            _dip = arp_pkt.dst_ip
            if arp_pkt.opcode == arp.ARP_REQUEST:
                print("   - Receives a ARP request packet from host {} ({}) asking MAC of {}".format(_sip,smac,_dip))

                self.ARP_table.setdefault(dpid,{})
                if (self.ARP_table[dpid].get(smac) != _sip):
                    self.ARP_table[dpid][smac] = _sip
                    print("   + Updates ARP table: MAC={} <-> IPv4={}".format(smac,_sip))

                have_arp_info = False

                for _dpid in self.ARP_table.key():
                    if _dip in self.ARP_table[_dpid].values():
                        for _dmac in self.ARP_table[_dpid].keys():
                            if self.ARP_table[_dpid][_dmac] == _dip:
                                break
                        print("     + Create and returns the ARP reply packet: IPv4={} <-> MAC={}".format(_dip,_dmac))
                        have_arp_info = True

                        e = ethernet.ethernet (dst=smac, src=_dmac, ethertype=ether.ETH_TYPE_ARP)
                        a = arp.arp(hwtype=1, proto=0x0800, hlen=6, plen=4, opcode=2, src_mac=_dmac, src_ip=_dip, dst_mac=smac, dst_ip=_sip)
                        p = packet.Packet()
                        p.add_protocol(e)
                        p.add_protocol(a)
                        p.serialize()

                        actions = [ofp_parser.OFPActionOutput(pin)]
                        out     = ofp_parser.OFPPacketOut(datapath=dp,buffer_id=ofp.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=p.data)
                        dp.send_msg(out)
                        break
                if (not have_arp_info):
                    print("     + {} is not in ARP table".format(_dip))
            return
                
        
        #Create the MAC table for swid
        self.MAC_table.setdefault(swid,{})

        #Learn Src. MAC
        self.MAC_table[swid][smac] = pin

        # MAC table lookup process
        if dmac in self.MAC_table[swid]:
            port_out = self.MAC_table[swid][dmac]
        else:
            port_out = ofp.OFPP_FLOOD


        # prepare and send FLOW MOD (add new enty to the OFS)
        actions = [ofp_parser.OFPActionOutput(port_out)]
        if ipv4h and icmpv6:
            inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            match = ofp_parser.OFPMatch(eth_type=0x800, ipv4_src=sipv4, ipv4_dst=dipv4, ip_proto=proto, icmpv4_type=icmptype)
            mod = ofp_parser.OFPFlowMod(datapath=dp, priority=1,match=match,instructions=inst)
            dp.send_msg(mod)


        # prepare and send PACKET-OUT
        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data  

        out = ofp_parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, 
            in_port=pin, actions=actions, data=data)
        dp.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def install_table_miss_flow(self, ev):
        msg = ev.msg
        dp  = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        #Prepare the Flow mod message
        actions = [ofp_parser.OFPActionOutput(
            ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [ofp_parser.OFPInstructionActions(
            ofp.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = ofp_parser.OFPFlowMod(datapath=dp, 
        priority=0,instructions=inst)

        dp.send_msg(mod)