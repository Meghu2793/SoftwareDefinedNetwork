from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_bool
import time
from database import MyDB

log = core.getLogger()

_flood_delay = 0


class LearningSwitch(object):

    def __init__(self, connection, transparent):

        self.connection = connection
        self.transparent = transparent

        self.macToPort = {}

        connection.addListeners(self)

        self.hold_down_expired = _flood_delay == 0
        self.db = MyDB()


    def get_action(self, transport_type, transport_srcport, transport_dstport, src_mac, dst_mac, src_ip, dst_ip):
        return self.db.get_action(transport_type, transport_srcport, transport_dstport, src_mac, dst_mac, src_ip, dst_ip)

    def take_action(self, packet, msg, event, port):
        if packet.find("ipv4") is not None \
                and (packet.find("tcp") is not None or packet.find("udp") is not None):
            if packet.find("tcp") is not None:
                transport_type = "tcp"
            else:
                transport_type = "udp"

            transport = packet.find(transport_type)
            transport_srcport = transport.srcport
            transport_dstport = transport.dstport

            src_mac = packet.src
            dst_mac = packet.dst

            ip_packet = packet.find("ipv4")
            src_ip = ip_packet.srcip
            dst_ip = ip_packet.dstip

            msg.match = of.ofp_match.from_packet(packet, event.port)


            action = self.get_action(transport_type, transport_srcport, transport_dstport, src_mac, dst_mac, src_ip, dst_ip)
            print action

            if action == "DP":
                None
            elif action == "HP":
                msg.actions.append(of.ofp_action_enqueue(port=port, queue_id=0))
            else:
                msg.actions.append(of.ofp_action_enqueue(port=port, queue_id=1))
        else:
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.actions.append(of.ofp_action_output(port=port))
        msg.data = event.ofp
        self.connection.send(msg)


    def _handle_PacketIn(self, event):
        packet = event.parsed

        def flood(message=None):
            msg = of.ofp_packet_out()
            if time.time() - self.connection.connect_time >= _flood_delay:

                if self.hold_down_expired is False:
                    self.hold_down_expired = True
                    log.info("%s: Flood hold-down expired -- flooding",
                             dpid_to_str(event.dpid))

                if message is not None: log.debug(message)
                msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            else:
                pass
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        def drop(duration=None):
            if duration is not None:
                if not isinstance(duration, tuple):
                    duration = (duration, duration)
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(packet)
                msg.idle_timeout = duration[0]
                msg.hard_timeout = duration[1]
                msg.buffer_id = event.ofp.buffer_id
                self.connection.send(msg)
            elif event.ofp.buffer_id is not None:
                msg = of.ofp_packet_out()
                msg.buffer_id = event.ofp.buffer_id
                msg.in_port = event.port
                self.connection.send(msg)

        self.macToPort[packet.src] = event.port

        if not self.transparent:
            if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
                drop()
                return

        if packet.dst.is_multicast:
            flood()
        else:
            if packet.dst not in self.macToPort:  # 4
                flood("Port for %s unknown -- flooding" % (packet.dst,))  # 4a
            else:
                port = self.macToPort[packet.dst]
                if port == event.port:  # 5
                    log.warning("Same port for packet from %s -> %s on %s.%s.  Drop."
                                % (packet.src, packet.dst, dpid_to_str(event.dpid), port))
                    drop(10)
                    return
                log.debug("installing flow for %s.%i -> %s.%i" %
                          (packet.src, event.port, packet.dst, port))
                msg = of.ofp_flow_mod()
                msg.idle_timeout = 10
                msg.hard_timeout = 30
                self.take_action(packet, msg, event, port)



class l2_learning(object):

    def __init__(self, transparent):
        core.openflow.addListeners(self)
        self.transparent = transparent

    def _handle_ConnectionUp(self, event):
        log.debug("Connection %s" % (event.connection,))
        LearningSwitch(event.connection, self.transparent)


def launch(transparent=False, hold_down=_flood_delay):
    try:
        global _flood_delay
        _flood_delay = int(str(hold_down), 10)
        assert _flood_delay >= 0
    except:
        raise RuntimeError("Expected hold-down to be a number")

    core.registerNew(l2_learning, str_to_bool(transparent))
