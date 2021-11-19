from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import switch_ofp1_3

class TrafficMonitor(switch_ofp1_3.Switch):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self.Periodic_Stats)        

    @set_ev_cls(ofp_event.EventOFPStateChange, [CONFIG_DISPATCHER, DEAD_DISPATCHER])
    def StateChange(self, ev):
        dp          = ev.datapath
        swid        = dp.id

        if ev.state == CONFIG_DISPATCHER:
            self.datapaths.setdefault(swid,dp)
        if ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(swid)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def FlowStatsReply(self, ev):
        msg         = ev.msg
        body        = msg.body
        dp          = msg.datapath
        Switch_id   = dp.id

        print('')
        print('{:^16} | {:^7} | {:^17} | {:^10} | {:^10} | {:^6}'.format('Switch ID', 'Port in', 'Dst. MAC', 'Pkt. count', 'Byte count', 'Action'))

        flow_list           = [flow for flow in body if flow.priority == 1]
        flow_list_sorted    = sorted(flow_list, key=lambda flow: (flow.match['in_port'], flow.match['eth_dst']))       
        
        for stat in sorted(flow_list_sorted):
            Port_in     = stat.match['in_port']
            MAC_dst     = stat.match['eth_dst']
            pkt_count   = stat.packet_count
            byte_count  = stat.byte_count
            Action      = stat.instructions[0].actions[0].port
            print('{:0>16} | {:^7} | {:^17} | {:^10} | {:^10} | {:^6}'.format(Switch_id, Port_in, MAC_dst, pkt_count, byte_count, Action))


    def Periodic_Stats(self):
        while 1:
            for dp in self.datapaths.values():
                ofp_parser    = dp.ofproto_parser
                FlowStats_req = ofp_parser.OFPFlowStatsRequest(dp)
                dp.send_msg(FlowStats_req)
            hub.sleep(10)