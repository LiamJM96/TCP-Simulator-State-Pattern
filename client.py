from socket import socket
import json
import random
from time import sleep


class State:

    # CurrentContext holds the values and states
    # used by the Client class
    CurrentContext = None

    def __init__(self, Context):
        self.CurrentContext = Context

    def trigger(self):
        return True


class StateContext:

    state = None
    CurrentState = None
    # states that can be used by the client
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

    def getStateIndex(self):
        return self.state


class Transition:
    '''base class for all methods that can be
    transitioned'''

    def syn(self):
        print "Error!"
        return False

    def ack(self):
        print "Error!"
        return False

    def rst(self):
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

    def timeout(self):
        print "Error!"
        return False

    def active_open(self):
        print "Error!"
        return False


class Closed(State, Transition):
    '''Closed attempts to connect to the server (Active Open)
    and sends a syn flag to the server in the Listen state'''

    def __init__(self, Context):
        State.__init__(self, Context)

    # connects to server and sends a syn flag
    def active_open(self):
        # if theres no connection
        if self.CurrentContext.socket is None:
            self.CurrentContext.make_connection()

        if self.CurrentContext.commands[0] == "syn":
            # Send syn to server and transition to SYN_SENT
            try:
                print "Sending syn to Server"
                # setting syn flag to True
                self.CurrentContext.packet['syn'] = True
                # using JSON to send data to the server
                packet_string = json.dumps(self.CurrentContext.packet)
                # Send the server the clients seq and ack number
                print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                        self.CurrentContext.packet['ack_number'])
                self.CurrentContext.socket.send(packet_string)
                print "\nTransitioning to state: SYN_SENT\n"
                self.CurrentContext.setState("SYN_SENT")
                return True
            except Exception as err:
                print "ERROR:", err, "\n"
                return False
        else:
            print "Error: Wrong command sent"
            print "Expected: syn, received:", self.CurrentContext.commands[0]
            return False

    # gets called when transitioning to the current state
    def trigger(self):

        # if client has finished connecting to server
        if self.CurrentContext.finish is True:
            print "Closing client..."
            return True

        return self.CurrentContext.active_open()


class Syn_Sent(State, Transition):
    '''Transitions to Syn_Sent after sending a syn flag
    from the Closed state and waits for the server to send
    a syn-ack. If so, client sends a ack back to the server'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def syn_ack(self):

        if self.CurrentContext.commands[1] == "ack":
            # send ack to server and transition to ESTABLISHED
            try:
                print "Sending ack to Server"
                # set the clients ack number to the servers seq number + 1
                self.CurrentContext.packet['ack_number'] = self.packet_string['seq_number'] + 1
                self.CurrentContext.packet['ack'] = True
                packet_string = json.dumps(self.CurrentContext.packet)
                # send the server the clients seq and ack number
                print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                        self.CurrentContext.packet['ack_number'])
                self.CurrentContext.socket.send(packet_string)
                print "\nTransitioning to state: ESTABLISHED\n"
                self.CurrentContext.setState("ESTABLISHED")
                return True
            except Exception as err:
                print "ERROR:", err, "\n"
                return False
        else:
            print "Error: Wrong command sent"
            print "Expected: ack, received:", self.CurrentContext.commands[1]
            return False

    # resets the socket connection by closing it
    def rst(self):
            print "Resetting connection"
            self.CurrentContext.socket.close()
            return True

    # closes the program if timeout occurs in syn_sent trigger
    def timeout(self):

            self.CurrentContext.finish = True
            print "Returning to CLOSED"
            self.CurrentContext.setState("CLOSED")
            return True

    def trigger(self):
        # recieve syn-ack from server, If no syn-ack is sent
        # timeout occurs after 5 seconds and closes program
        try:
            # increment the clients seq number by 1
            self.CurrentContext.packet['seq_number'] += 1
            self.CurrentContext.socket._sock.settimeout(5)
            command = self.CurrentContext.socket.recv(1024)
            self.packet_string = json.loads(command)
        except:
            print "ERROR: Socket timed out in SYN_SENT\n"
            self.CurrentContext.packet["syn"] = False
            self.CurrentContext.packet["rst"] = True
            return self.CurrentContext.timeout()

        if self.packet_string['rst'] is True:
            return self.CurrentContext.rst()

        # receives the syn-ack and sends ack to server
        if self.packet_string['syn'] is True and self.packet_string['ack'] is True:
            print "Receiving syn ack from Server"
            # receive the servers seq and ack number
            print "Received: {} (Seq), {} (Ack)".format(self.packet_string['seq_number'],
                                                        self.packet_string['ack_number'])
            return self.CurrentContext.syn_ack()
        else:
            return False


class Established(State, Transition):
    '''sends messages to the server as both client and server
    are now in the ESTABLISHED state allowing the ability to
    send messages. Once messages are finished sending,
    the client sends a syn flag to the server notifying that
    it has finished and is ready to close the connection'''

    def __init__(self, Context):
        State.__init__(self, Context)

    # sends a fin to the server after senind all messages
    #  before transition to FIN_WAIT_1
    def close(self):

        if self.CurrentContext.commands[2] == "fin":

            try:
                print "Sending fin to Server"
                self.CurrentContext.packet['fin'] = True
                packet_string = json.dumps(self.CurrentContext.packet)
                # send the clients seq and ack number to the server
                print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                        self.CurrentContext.packet['ack_number'])
                self.CurrentContext.socket.send(packet_string)
                print "\nTransitioning to state: FIN_WAIT_1\n"
                self.CurrentContext.setState("FIN_WAIT_1")
                return True
            except Exception as err:
                print "ERROR:", err, "\n"
                return False
        else:
            print "Error: Wrong command sent"
            print "Expected: fin, received:", self.CurrentContext.commands[2]
            return False

    def trigger(self):

        print "Sending messages to server..."

        # sends each message indvidually for every message in the list
        for message in self.CurrentContext.messages:
            try:
                sleep(1)    # allows the server to stay in sync with the client
                self.CurrentContext.packet["message"] = message
                packet_string = json.dumps(self.CurrentContext.packet)
                self.CurrentContext.socket.send(packet_string)
            except Exception as err:
                print "ERROR:", err, "\n"
                return False

        print "All messages sent"

        # reset message to empty and send so server knows theres no messages to receive
        try:
            self.CurrentContext.packet['message'] = ""
            packet_string = json.dumps(self.CurrentContext.packet)
            self.CurrentContext.socket.send(packet_string)
        except Exception as err:
            print "ERROR:", err, "\n"
            return False

        return self.CurrentContext.close()


class Fin_Wait_1(State, Transition):
    '''Waits to receive an ack flag from the server
    acknowledging that it wants to close the connection
    before transitioning to FIN_WAIT_2'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def ack(self):
        print "\nTransitioning to state: FIN_WAIT_2\n"
        self.CurrentContext.setState("FIN_WAIT_2")
        return True

    def trigger(self):

        try:
            # receives ack flag from server
            # increment the clients seq number by 1
            self.CurrentContext.packet['seq_number'] += 1
            command = self.CurrentContext.socket.recv(1024)
            packet_string = json.loads(command)
        except Exception as err:
            print "ERROR:", err, "\n"
            return False

        if packet_string['ack'] is True:
            print "Receiving ack from Server"
            # Receive servers seq and number
            print "Received: {} (Seq), {} (Ack)".format(packet_string['seq_number'],
                                                        packet_string['ack_number'])
            return self.CurrentContext.ack()
        else:
            return False


class Fin_Wait_2(State, Transition):
    '''Waits to receive a fin flag from the server
    notifying the client that its okay to close the connection.
    The client then sends an ack flag to the server acknowledging
    the fin flag'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def fin(self):
        if self.CurrentContext.commands[3] == "ack":

            try:
                # send ack flag to server before transitioning to TIMED_WAIT
                print "Sending ack to Server"
                # set the clients ack number to the servers seq number + 1
                self.CurrentContext.packet['ack_number'] = self.packet_string['seq_number'] + 1
                self.CurrentContext.packet['ack'] = True
                packet_string = json.dumps(self.CurrentContext.packet)
                # send the clients syn and ack number to the server
                print "Sent: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                        self.CurrentContext.packet['ack_number'])
                self.CurrentContext.socket.send(packet_string)
                print "\nTransitioning to state: TIMED_WAIT\n"
                self.CurrentContext.setState("TIMED_WAIT")
                return True
            except Exception as err:
                print "ERROR:", err, "\n"
                return False
        else:
            print "Error: Wrong command sent"
            print "Expected: ack, received:", self.CurrentContext.commands[3]
            return False

    def trigger(self):

        try:
            # receive fin from server
            command = self.CurrentContext.socket.recv(1024)
            self.packet_string = json.loads(command)
        except Exception as err:
                print "ERROR:", err, "\n"
                return False

        if self.packet_string['fin'] is True:
            print "Receiving fin from Server"
            # receive the servers seq and ack numbers
            print "Received: {} (Seq), {} (Ack)".format(self.CurrentContext.packet['seq_number'],
                                                        self.CurrentContext.packet['ack_number'])
            return self.CurrentContext.fin()
        else:
            return False


class Timed_Wait(State, Transition):
    '''Timed_Wait waits 5 seconds for the server for the
    server to receive the ack flag by keeping the connection
    open before closing to prevent any data being sent elsewhere'''

    def __init__(self, Context):
        State.__init__(self, Context)

    def timeout(self):
        # closes the socket and transitions to CLOSED
        # to close the client
        self.CurrentContext.socket.close()
        self.CurrentContext.finish = True
        print "\nTransitioning to state: CLOSED\n"
        self.CurrentContext.setState("CLOSED")
        return True

    def trigger(self):
        # simulating the timed_wait by keeping connection open
        # allowing server to receive the ack
        print "Timed wait for", self.CurrentContext.sleep_time, "seconds..."
        sleep(self.CurrentContext.sleep_time)   # sleep time = 5
        return self.CurrentContext.timeout()


class Client(StateContext, Transition):
    '''Main class that initialises all the values
    and states that it can use across the program
    to simulate a TCP client'''

    # initialise the starting values for the client
    def __init__(self):
        self.sleep_time = 5  # puts pauses in scripts for demo. 0 otherwise
        self.host = "127.0.0.1"
        self.port = 5000
        self.connection_address = 0
        self.socket = None
        self.finish = False
        # packet and its flags
        # False = disabled, True = enabled
        self.packet = {"syn": False, "fin": False, "rst": False, "ack": False, "seq_number": random.randint(0, 100),
                                                                               "ack_number": 0, "message": ""}
        # lists that hold the commands and messages respectively
        # after being catergorised using JSON format in the loadCommandFile method
        self.commands = []
        self.messages = []

        # initialising the states to be used by the client
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["SYN_SENT"] = Syn_Sent(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["FIN_WAIT_1"] = Fin_Wait_1(self)
        self.availableStates["FIN_WAIT_2"] = Fin_Wait_2(self)
        self.availableStates["TIMED_WAIT"] = Timed_Wait(self)
        # load commands and messages
        self.loadCommandsFile()
        # transition to the starting state for the client
        print "\nTransitioning to state: CLOSED\n"
        self.setState("CLOSED")

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

    def timeout(self):
        return self.CurrentState.timeout()

    def active_open(self):
        return self.CurrentState.active_open()

    def make_connection(self):
        ''' this method initiates an outbound connection'''
        print "Attempting to connect to the server..."
        self.socket = socket()
        try:
            self.socket.connect((self.host, self.port))
            self.connection_address = self.host
            print "Connected\n"
            return True
        except Exception as err:
            print err
            exit()

    def loadCommandsFile(self):
        ''' this method loads the commands and messages
        from the txt file using JSON format and separates
        them into two separate lists'''

        print "\nLoading commands and messages from text file..."

        # read JSON from txt file and deserialise it
        try:
            # open file for reading
            command_file = open('client_commands.txt', 'r')
            command_list = json.loads(command_file.read())
            command_file.close()
        # if IOError raised, file cannot be loaded
        except IOError:
            print "File could not be found"
            exit()

        temp_commands = command_list["commands"]
        temp_messages = command_list["messages"]

        for command in temp_commands:
            self.commands.append(command["command"])

        for message in temp_messages:
            self.messages.append(message["message"])

        print "Commands loaded successfully"
        print "Commands: -", self.commands
        print "Messages: -", self.messages, "\n"


if __name__ == '__main__':

    MyClient = Client()
