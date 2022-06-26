from socket import socket
import json
import random


class State:
    # CurrentContext holds the values and states
    # used by the Server class
    CurrentContext = None

    def __init__(self, Context):
        self.CurrentContext = Context

    def trigger(self):
        return True


class StateContext:
    state = None
    CurrentState = None
    # states that can be used by the server
    availableStates = {}

    # changes state when called and activates
    # the trigger for that specified state
    def setState(self, newstate):
        try:
            self.CurrentState = self.availableStates[newstate]
            self.state = newstate
            self.CurrentState.trigger()
            return True
        except KeyError:    # wrong state key specified
            return False

    def getState(self):
        return self.state


class Transition:
    '''base class for all methods that can be
    transitioned'''

    def passive_open(self):
        print "Error!"
        return False

    def syn(self):
        print "Error!"
        return False

    def ack(self):
        print "Error!"
        return False

    def syn_ack(self):
        print "Error!"
        return False

    def close(self):
        print "Error!"
        return False

    def fin(self):
        print "Error!"
        return False


class Closed(State, Transition):
    '''Closed state establishes a connection and waits for a
    client to connect, if theres a connection, move to the
    Listen state'''

    def __init__(self, Context):
        State.__init__(self, Context)

    # waits for client connection and moves to LISTEN
    # if connection is successful
    def passive_open(self):
        if self.CurrentContext.connection is None:
            self.CurrentContext.listen()
        print "Transitioning to state: LISTEN\n"
        self.CurrentContext.setState("LISTEN")
        return True

    def trigger(self):
        if self.CurrentContext.finish is True:
            print "Closing server..."
            return True

        return self.CurrentContext.passive_open()


class Listen(State, Transition):
    '''Listen waits until it receives a syn flag from
    the client and sends a syn-ack back before transitioning
    to SYN_RECEIVED '''

    def __init__(self, Context):
        State.__init__(self, Context)

    # sends a syn-ack to the client and transitions to SYN_RECEIVED
    def syn_ack(self):

        try:
            print "Sending syn_ack to client..."
            # sets the ack number as the clients seq number + 1
            self.CurrentContext.packet['ack_number'] = self.packet_string['seq_number'] + 1
            # setting syn and ack flag to True
            self.CurrentContext.packet['syn'] = True
            self.CurrentContext.packet['ack'] = True
            # using JSON to send data
            sendpacket_string = json.dumps(self.CurrentContext.packet)
            # send servers seq and ack number to client
            print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                    self.CurrentContext.packet['ack_number'])
            self.CurrentContext.connection.send(sendpacket_string)
            print "\nTransitioning to state: SYN_RECEIVED\n"
            self.CurrentContext.setState("SYN_RECEIVED")
            return True
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

    def trigger(self):

        # receives a syn from the client and sends
        # a syn-ack back
        try:
            command = self.CurrentContext.connection.recv(1024)
            self.packet_string = json.loads(command)
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

        if self.packet_string['syn'] is True:
            print "Receiving syn from client..."
            # receive clients seq and ack number
            print "Received: {} (Seq), {} (Ack)".format(self.packet_string['seq_number'],
                                                        self.packet_string['ack_number'])
            return self.CurrentContext.syn_ack()
        else:
            return False


class Syn_Received(State, Transition):
    '''Waits to receive an ack flag from the client
    before transitioning to ESTABLISHED to receive messages'''

    def __init__(self, Context):
        State.__init__(self, Context)

    # transition to ESTABLISHED after receiving ack
    def ack(self):
        print "\nTransitioning to state: ESTABLISHED\n"
        self.CurrentContext.setState("ESTABLISHED")

    def trigger(self):

        # receives an ack flag from the client
        try:
            # increments the server seq number
            self.CurrentContext.packet['seq_number'] += 1
            command = self.CurrentContext.connection.recv(1024)
            self.packet_string = json.loads(command)
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

        if self.packet_string['ack'] is True:
            print "Received ack from Client"
            # receive clients seq and ack number
            print "Received: {} (Seq), {} (Ack)".format(self.packet_string['seq_number'],
                                                        self.packet_string['ack_number'])
            return self.CurrentContext.ack()
        else:
            return False


class Established(State, Transition):
    '''Receives messages from the client as they're
    both in the ESTABLISHED state. Once the client has finished
    sending all the messages, it receives one final message notifying
    it has finished sending. After this, the client sends a fin flag
    meaning it wants to close the connection and the server sends
    an ack flag back to the server to let it know its okay to close'''

    def __init__(self, Context):
        State.__init__(self, Context)

    # sends ack to client after acknowledging the fin flag
    # sent from the client before transitioning to CLOSE_WAIT
    def fin(self):

        try:
            print "Sending ack to Client"
            # setting servers ack number to clients seq number + 1
            self.CurrentContext.packet['ack_number'] = self.packet_string['seq_number'] + 1
            self.CurrentContext.packet['ack'] = True
            packet_string = json.dumps(self.CurrentContext.packet)
            # send client the server seq and ack numbers
            print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                    self.CurrentContext.packet['ack_number'])
            self.CurrentContext.connection.send(packet_string)
            print "\nTransitioning to state: CLOSE_WAIT\n"
            self.CurrentContext.setState("CLOSE_WAIT")
            return True
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

    def trigger(self):

        try:
            # receive first message
            command = self.CurrentContext.connection.recv(1024)
            self.packet_string = json.loads(command)

            print "Receiving messages from Client:"
            # loops until the client has sent all of its messages
            # by sending an empty string to let it know its finished
            while not self.packet_string["message"] == "":
                print "Message:", self.packet_string["message"]
                command = self.CurrentContext.connection.recv(1024)
                self.packet_string = json.loads(command)

            # receive fin flag
            command = self.CurrentContext.connection.recv(1024)
            self.packet_string = json.loads(command)
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

        if self.packet_string['fin'] is True:
            print "Received fin from Client"
            # Receive the clients seq and ack number
            print "Received: {} (Seq), {} (Ack)".format(self.packet_string['seq_number'],
                                                        self.packet_string['ack_number'])
            return self.CurrentContext.fin()


class Close_Wait(State, Transition):
    '''Sends a fin flag to the client before transitioning to the
    LAST_ACK state to wait for a ack from the client'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def close(self):

        try:
            # sends a fin flag to the client notifying
            # the client its closing the connection
            # before transitioning to LAST_ACK
            print "Sending fin to Client"
            self.CurrentContext.packet['fin'] = True
            packet_string = json.dumps(self.CurrentContext.packet)
            # send seq and ack number to client
            print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                    self.CurrentContext.packet['ack_number'])
            self.CurrentContext.connection.send(packet_string)
            print "\nTransitioning to state: LAST_ACK\n"
            self.CurrentContext.setState("LAST_ACK")
            return True
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

    def trigger(self):
        return self.CurrentContext.close()


class Last_Ack(State, Transition):
    '''Waits to receive the final ack from the client
    acknowledging that its okay to close the connection.
    Once the ack flag is received the server transitions to CLOSED
    and closes the server'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def ack(self):
        # closes the connection and transitions to CLOSED
        self.CurrentContext.connection.close()
        self.CurrentContext.finish = True
        print "\nTransitioning to state: CLOSED\n"
        self.CurrentContext.setState("CLOSED")

    def trigger(self):

        try:
            # receive the ack flag from the client
            # increment the servers seq number by 1
            self.CurrentContext.packet['seq_number'] += 1
            command = self.CurrentContext.connection.recv(1024)
            packet_string = json.loads(command)
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

        if packet_string['ack'] is True:
            print "Receiving ack from Client"
            # Receive clients seq and ack number
            print "Received: {} (Seq), {} (Ack)".format(packet_string['seq_number'],
                                                        packet_string['ack_number'])
            return self.CurrentContext.ack()
        else:
            return False


class Server(StateContext, Transition):
    '''Main class that initialises all the values
    and states that it can use across the program
    to simulate a TCP server'''

    # initialise starting values for server
    def __init__(self):
        self.sleep_time = 2  # puts pauses in scripts for demo. 0 otherwise
        self.host = "127.0.0.1"
        self.port = 5000
        self.socket = None
        self.connection = None
        # packet and its flags
        # False = disabled, True = enabled
        self.packet = {"syn": False, "fin": False, "rst": False, "ack": False, "seq_number": random.randint(0, 100),
                                                                               "ack_number": 0, "message": ""}
        self.finish = False

        # initialising the states to be used by the client
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["LISTEN"] = Listen(self)
        self.availableStates["SYN_RECEIVED"] = Syn_Received(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["CLOSE_WAIT"] = Close_Wait(self)
        self.availableStates["LAST_ACK"] = Last_Ack(self)

        # transition to the starting state for the client
        print "\nTransitioning to starting state: CLOSED\n"
        self.setState("CLOSED")

    def passive_open(self):
        return self.CurrentState.passive_open()

    def syn(self):
        return self.CurrentState.syn()

    def ack(self):
        return self.CurrentState.ack()

    def rst(self):
        return self.CurrentState.rst()

    def syn_ack(self):
        return self.CurrentState.syn_ack()

    def close(self):
        return self.CurrentState.close()

    def fin(self):
        return self.CurrentState.fin()

    def listen(self):
        ''' this method initiates a listen socket'''
        self.socket = socket()
        try:
            print "Waiting for connection request..."
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            # connection acceptance
            self.connection, self.connection_address = self.socket.accept()
            print "Connected successfully to:", self.connection_address, "\n"
            return True
        except Exception as err:
            print err
            exit()


if __name__ == '__main__':

    MyServer = Server()
