# -*- coding: cp1252 -*-
import os
import zipfile
import threading
import serialData
import time
from sys import stdout, exit
from struct import *
import kbhit
from os import name
from glob import glob

# colocar aqui o diretório do arquivo usando barra dupla (\\)
# Mudar isso para ser mais generico (Apos teste funcionando)
# path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
# path2 = 'C:\\Users\\Usuário\\Desktop'
# os.chdir(path)

if name == 'nt':
    number = raw_input("Qual o numero da porta COM na qual o arduino esta conectado?")
    port = "COM" + str(number)
elif name == 'posix':
    port_list = []
    port_list += glob('/dev/tty.usbmodem*') + glob('/dev/ttyACM*') + glob('/dev/ttyUSB*')
    port = port_list[0]

# Max baud rate = 1000000
baud_rate = 1000000
# Voce precisa de um objeto serial_interface pra enviar dados. O metodo send_data nao eh estatico!!

serial_interface = serialData.SerialInterface(port, baud_rate)

# constantes do protocolo
send_request = bytearray([1])
send_ok = bytearray([2])
msg_start_byte = bytearray([3])

# variaveis globais
msg = bytearray([])
# Essa msg_arrived_flag eh true quando uma resposta chegou? O nome ta meio dificil de entender. Talvez mudar o nome?
# Na verdade o nome de todos os eventos podiam ser mais claros. Um pouco mais descritivos. Deixaria o codigo mais
# facil de ler.
msg_arrived_flag = threading.Event()
stop = threading.Event()
interrupt = threading.Event()
stop_program = threading.Event()
ans = 's'

kb = kbhit.KBHit()

try:
    while not serial_interface.is_link_up():
        time.sleep(0.1)
except KeyboardInterrupt:
    serial_interface.stop_serial()
    exit()


def send_file():
    global msg, ans
    try:
        while ans == 's' or ans == 'S' and not stop_program.is_set():
            # Talvez um sleep aqui?
            while not interrupt.is_set() and (ans == 's' or ans == 'S') and not stop_program.is_set():
                # lê o nome e a extebsão do arquivo
                # name = raw_input("Digite o nome do arquivo que deseja enviar: ")
                # ext = raw_input("Digite a extensão do arquivo: ")

                print "Digite o nome do arquivo que deseja enviar: "
                name = ''
                while not stop.is_set() and not interrupt.is_set() and not stop_program.is_set():
                    if kb.kbhit():
                        c = kb.getch()
                        stdout.write(c)
                        stdout.flush()
                        if ord(c) == 27:
                            stop.set()
                        else:
                            name += c
                if stop_program.is_set():
                    serial_interface.stop_serial()
                    exit()
                if interrupt.is_set():
                    stop.clear()
                    break
                print "Digite a extensão do arquivo: "
                stop.clear()
                ext = ''
                while not stop.is_set() and not interrupt.is_set() and not stop_program.is_set():
                    if kb.kbhit():
                        c = kb.getch()
                        stdout.write(c)
                        stdout.flush()
                        if ord(c) == 27:
                            stop.set()
                        else:
                            ext += c
                if stop_program.is_set():
                    serial_interface.stop_serial()
                    exit()
                if interrupt.is_set():
                    stop.clear()
                    break
                stop.clear()
                arq = name + "." + ext

                # data_byte = bytearray(data)
                # N_byte = bytearray(pack('i', len(data_byte)))
                try:
                    N_byte = bytearray(pack('i', os.stat(arq).st_size))
                except OSError:
                    print "/nFile not found."
                    ans = raw_input("Gostaria de enviar ou receber outro arquivo? (s/n): ")
                    continue
                text_array = bytearray()
                for character in arq:
                    text_array.append(ord(character))
                msg = send_request + N_byte + text_array
                serial_interface.send_data(msg)
                t0 = time.clock()
                while time.clock()-t0 < 30:
                    time.sleep(0.1)
                    if msg_arrived_flag.is_set():
                        break

                if msg_arrived_flag.is_set():
                    if msg == send_ok:
                        # cria um zip e adiciona o arquivo
                        zf = zipfile.ZipFile(name + ".zip", 'w')
                        zf.write(arq)
                        zf.close()
                        # lê o arquivo zipado como binário
                        with open(name + ".zip", 'rb') as f:
                            data = f.read()
                        os.remove(name + ".zip")
                        data_byte = bytearray(data)
                        print len(data_byte)
                        serial_interface.send_data(msg_start_byte + data_byte)
                        msg_arrived_flag.clear()
                        # adicionar algum feedback aqui.
                        print "Arquivo enviado com sucesso!"
                    else:
                        print "Falha ao enviar o arquivo"
                ans = raw_input("Gostaria de enviar ou receber outro arquivo? (s/n): ")
    except KeyboardInterrupt:
        stop_program.set()
        serial_interface.stop_serial()
        exit()


def receive_file():
    global msg, ans
    try:
        while (ans == 's') or (ans == 'S') and not stop_program.is_set():
            while serial_interface.message_queue_is_empty() and not stop_program.is_set() and ((ans == 's') or (ans == 'S')):
                time.sleep(0.01)

            msg = serial_interface.get_message()

            # eh necessario colocar o [0] depois do send request, do contrario vamos comparar um inteiro com um bytearray e
            # isso nunca vai dar True. (quando pegamos somente um elemento da bytearray ele retorna um inteiro
            if msg[0] == send_request[0]:
                interrupt.set()
                # O usuario nao sabe o nome do arquivo ou o tamanho dele. Alem disso, vc envia o ok, o usuario querendo o
                # arquivo ou nao :P
                N_tuple = unpack('i', str(msg[1:5]))
                N = N_tuple[0]
                file_name = str(msg[5:])
                receive_ans = raw_input("\nDeseja receber o arquivo " + file_name + "(tamanho: " + str(N) + "? (s/n): ")
                if receive_ans == 's' or receive_ans == 'S':
                    msg_arrived_flag.set()
                    serial_interface.send_data(send_ok)
            elif msg[0] == msg_start_byte[0]:
                received = str(msg[1:])
                print len(received)
                # N nao eh o tamanho do arquivo? Nesse caso vc vai acessar indices de file_name que nao existem e tera uma
                # exception aqui. N aparentemente nao eh usado pra nada. Quando eu falei de colocar isso na request seria
                # pra informar o usuario do tamanho do arquivo a ser enviado. Aqui vc pode fazer range(len(file_name)) ou
                # so faz um file_name.index('.') (acho que isso eh o melhor a se fazer.
                # Abraço: problema corrigido, usei o index =D
                dot = file_name.index('.')
                r_name = file_name[0:dot]
                # r_ext nao serve pra nada
                # r_ext = file_name[dot+1:]
                with open(r_name + ".zip", 'wb') as g:
                    g.write(received)
                # TODO: put exception here for when the zip file is corrupted
                try:
                    zfile = zipfile.ZipFile(r_name + ".zip")
                    zfile.extract(file_name)
                except zipfile.BadZipfile:
                    print "File arrived corrupted!"
                zfile.close()
                os.remove(r_name + ".zip")
                interrupt.clear()
            else:
                msg_arrived_flag.set()
    except KeyboardInterrupt:
        exit()

sending = threading.Thread(target=send_file)
receiving = threading.Thread(target=receive_file)

sending.start()
receiving.start()

try:
    sending.join()
    receiving.join()
except KeyboardInterrupt:
    stop_program.set()
    serial_interface.stop_serial()
    exit()

# simulando a recepção
# recebido_byte = bytearray(N)
# for i in range(0, N):
#    recebido_byte[i] = data_byte[i]
#
# recebido = str(recebido_byte)
#
# with open(name + "_saida.zip", 'wb') as g:
#    g.write(recebido)
#
# zfile = zipfile.ZipFile(name + "_saida.zip")
# zfile.extract(arq, path2)
# zfile.close()
# os.remove(name + "_saida.zip"
