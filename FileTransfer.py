# -*- coding: cp1252 -*-
import os
import zipfile
import threading
import serialData
import time
from struct import *
import kbhit

# colocar aqui o diretório do arquivo usando barra dupla (\\)
# Mudar isso para ser mais generico (Apos teste funcionando)
# path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
# path2 = 'C:\\Users\\Usuário\\Desktop'
# os.chdir(path)
# Coloca o nome da port do arduino aqui
port = "/dev/tty.usbmodem1411"
# Max baud rate = 1000000
baud_rate = 115200
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
ans = 's'

kb = kbhit.KBHit()


def send_file():
    global msg, ans
    while ans == 's' or ans == 'S':
        # Talvez um sleep aqui?
        while not interrupt.is_set():
            # lê o nome e a extebsão do arquivo
            # name = raw_input("Digite o nome do arquivo que deseja enviar: ")
            # ext = raw_input("Digite a extensão do arquivo: ")

            print "Digite o nome do arquivo que deseja enviar: "
            name = ''
            while not stop.is_set() and not interrupt.is_set():
                if kb.kbhit():
                    c = kb.getch()
                    print c,
                    if ord(c) == 13:
                        stop.set()
                    else:
                        name += c
            if interrupt.is_set():
                stop.clear()
                break
            print "Digite a extensão do arquivo: "
            stop.clear()
            ext = ''
            while not stop.is_set() and not interrupt.is_set():
                if kb.kbhit():
                    c = kb.getch()
                    print c,
                    if ord(c) == 13:
                        stop.set()
                    else:
                        ext += c
            if interrupt.is_set():
                stop.clear()
                break

            arq = name + "." + ext

            # Felipe: Talvez seja melhor so criar o arquivo depois de confirmado que pode ser enviado?
            # O unico problema associado a isso seria um possivel delay entre receber a resposta e enviar o arquivo
            # enquanto ele eh zipado e lido.
            

            # prepara e envia o aqrquivo

            # data_byte = bytearray(data)
            # N_byte = bytearray(pack('i', len(data_byte)))
            N_byte = bytearray(pack('i', os.stat(arq).st_size))

            msg = send_request + N_byte + bytearray(arq)
            serial_interface.send_data(msg)
            t0 = time.clock()
            while time.clock()-t0 < 30:
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
                    serial_interface.send_data(msg_start_byte + data_byte)
                    msg_arrived_flag.clear()
                    print "Arquivo enviado com sucesso!"
                else:
                    print "Falha ao enviar o arquivo"

            ans = raw_input("Gostaria de enviar ou receber outro arquivo? (s/n): ")


def receive_file():
    global msg, ans
    while (ans == 's') or (ans == 'S'):
        while serial_interface.message_queue_is_empty():
            time.sleep(0.01)
            pass

        msg = serial_interface.get_message()

        # eh necessario colocar o [0] depois do send request, do contrario vamos comparar um inteiro com um bytearray e
        # isso nunca vai dar True. (quando pegamos somente um elemento da bytearray ele retorna um inteiro
        if msg[0] == send_request[0]:
            interrupt.set()
            # O usuario nao sabe o nome do arquivo ou o tamanho dele. Alem disso, vc envia o ok, o usuario querendo o
            # arquivo ou nao :P
            receive_ans = raw_input("\nDeseja receber um arquivo? (s/n): ")
            if receive_ans == 's':
                N_tuple = unpack('i', str(msg[1:5]))
                N = N_tuple[0]
                file_name = str(msg[5:])
                msg_arrived_flag.set()
                serial_interface.send_data(send_ok)
        elif msg[0] == msg_start_byte[0]:
            received = str(msg[1:])
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
            zfile = zipfile.ZipFile(r_name + ".zip")
            zfile.extract(file_name)
            zfile.close()
            os.remove(r_name + ".zip")
            interrupt.clear()
        else:
            msg_arrived_flag.set()


sending = threading.Thread(target=send_file)
receiving = threading.Thread(target=receive_file)

sending.start()
receiving.start()

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
