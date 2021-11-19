from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

class Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Switch, self).__init__(*args, **kwargs)
        self.MAC_table = {} #MAC address Table

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        
        #need: mac addr, port in, switch id
        pkt    = packet.Packet(msg.data)
        etherh = pkt. get_protocol(ethernet.ethernet)
        smac   = etherh.src
        dmac   = etherh.dst
        pin    = msg.match['in_port']
        swid   = dp.id

        #Create MAC address table for each Switch (ID)
        self.MAC_table.setdefault(swid,{})
        
        #LEARN MAC address
        #Add MAC to port ID
        self.MAC_table[swid][smac] = pin
        
        #LOOKUP MAC address in the table
        if dmac in self.MAC_table[swid]:
            port_out = self.MAC_table[swid][dmac]
        else:
            port_out = ofp.OFPP_FLOOD
                    
        
        #Send Packet-Out message
        actions = [ofp_parser.OFPActionOutput(port_out)]

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data=msg.data

        out = ofp_parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, 
                                      in_port=pin,actions=actions, 
                                      data=data)
        dp.send_msg(out) 

        #If Dest MAC is in table, add flow entry to switch
        if port_out != ofp.OFPP_FLOOD:
            match = ofp_parser.OFPMatch(in_port=pin, eth_dst=dmac)
            inst  = [ofp_parser.OFPInstructionActions(
                            ofp.OFPIT_APPLY_ACTIONS, actions)]
            out   = ofp_parser.OFPFlowMod(datapath=dp, priority=1, 
                                          match=match, instructions=inst)
            dp.send_msg(out)


            
        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def install_table_miss_flow(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                              ofp.OFPCML_NO_BUFFER)]
        match = ofp_parser.OFPMatch()
        inst  = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                                  actions)]
        out   = ofp_parser.OFPFlowMod(datapath=dp, priority=0, 
                                          match=match, instructions=inst)
        dp.send_msg(out)