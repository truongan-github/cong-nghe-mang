"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        sever1 = self.addHost( 'srv1' , ip='192.168.1.201/24')
        sever2 = self.addHost( 'srv2' , ip='192.168.1.202/24')

        host_1 = self.addHost( 'h1', ip='192.168.1.1/24')
        host_2 = self.addHost( 'h2', ip='192.168.1.2/24')
        host_3 = self.addHost( 'h3', ip='192.168.1.3/24')

        Sw_1 = self.addSwitch( 's1' )
        Sw_2 = self.addSwitch( 's2' )
        Sw_3 = self.addSwitch( 's3' )
        Sw_4 = self.addSwitch( 's4' )
        Sw_5 = self.addSwitch( 's5' )
        Sw_6 = self.addSwitch( 's6' )
        Sw_7 = self.addSwitch( 's7' )
        Sw_8 = self.addSwitch( 's8' )
       

        # Add links
        linkopts1 = dict(bw=1000, delay='5ms')
        linkopts2 = dict(bw=100, delay='1ms')

        self.addLink( Sw_1, Sw_2, **linkopts1)
        self.addLink( Sw_1, Sw_3, **linkopts1)

        self.addLink( Sw_2, Sw_4, **linkopts1)
        self.addLink( Sw_2, Sw_5, **linkopts1)
        self.addLink( Sw_2, Sw_6, **linkopts1)

        self.addLink( Sw_3, Sw_7, **linkopts1)
        self.addLink( Sw_3, Sw_8, **linkopts1)
        self.addLink( Sw_4, host_1, **linkopts2)
        self.addLink( Sw_5, host_2, **linkopts2)
        self.addLink( Sw_6, host_3, **linkopts2)
        self.addLink( Sw_7, sever1, **linkopts2)
        self.addLink( Sw_8, sever2, **linkopts2)


topos = { 'mytopo': ( lambda: MyTopo() ) }
