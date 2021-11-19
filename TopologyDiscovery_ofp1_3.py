from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.lib import hub

class TopologyDiscovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TopologyDiscovery, self).__init__(*args, **kwargs)
        self.Topology_db = {}
        self.network_changed_thread = hub.spawn_after(1,None)    

    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        print("Switch entering---------------")
        hub.kill(self.network_changed_thread)
        self.network_changed_thread = hub.spawn_after(1,self.network_changed)

    @set_ev_cls(event.EventSwitchLeave)
    def handler_switch_leave(self, ev):
        print("Switch leaving---------------")
        hub.kill(self.network_changed_thread)
        self.network_changed_thread = hub.spawn_after(1,self.network_changed)

    def network_changed(self):
        self.topo_raw_switches = get_switch(self, None)
        self.topo_raw_links    = get_link(self, None)

        print("\nCurrent Links:")
        for l in self.topo_raw_links:
            print (str(l))

        print("\nCurrent Switches:")
        for s in self.topo_raw_switches:
            print (str(s))
        
        print("")
        self.BuildTopology()

    def BuildTopology(self):
        self.Topology_db.clear()

        for l in self.topo_raw_links:
            _dpid_src = l.src.dpid
            _dpid_dst = l.dst.dpid
            _port_src = l.src.port_no
            _port_dst = l.dst.port_no
            
            self.Topology_db.setdefault(_dpid_src,{})
            self.Topology_db[_dpid_src][_dpid_dst] = [_port_src,_port_dst]
        print("\nTopology Database -------------------------------")
        print(self.Topology_db)