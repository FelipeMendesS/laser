# -*- coding: cp1252 -*-
import os
import zipfile
import threading
import serialData
import time
from struct import *

# constantes do protocolo
send_request = bytearray([1])
send_ok = bytearray([2])
msg_start_byte = bytearray([3])

# variaveis globais
msg = bytearray([])
msg_arrived_flag = threading.Event()
ans = 's'

def send_file():
    while (ans == 's') or (ans == 'S'):
        # lê o nome e a extebsão do arquivo
        name = raw_input("Digite o nome do arquivo que deseja enviar: ")
        ext = raw_input("Digite a extensão do arquivo: ")
        arq = name + "." + ext

        # cria um zip e adiciona o arquivo
        zf = zipfile.ZipFile(name + ".zip", 'w')
        zf.write(arq)
        zf.close()

        # lê o arquivo zipado como binário
        with open(name + ".zip",'rb') as f:
            data = f.read()
        os.remove(name + ".zip")


        # prepara e envia o aqrquivo
        data_byte = bytearray(data)
        N_byte = bytearray(pack('i', len(data_byte)))

        msg = send_request + N_byte + bytearray(arq)
        serialData.send_data(msg)
        t0 = time.clock()
        while (time.clock()-t0 < 30):
            if msg_arrived_flag.is_set():
                break

        if msg_arrived_flag.is_set():
            if msg == send_ok:
                serialData.send_data(msg_start_byte + data_byte)
                msg_arrived_flag.clear()
        
        ans = raw_input("Gostaria de enviar ou receber outro arquivo? (s/n): ")

def receive_file():
    while (ans == 's') or (ans == 'S'):
        while serialData.message_queue_is_empty():
            time.sleep(0.01)
            pass

        msg = serialData.get_message()

        if msg[0] == send_request:
            serialData.send_data(send_ok)
            N_tuple = unpack('i',str(msg[1:5]))
            N = N_tuple[0]
            file_name = str(msg[5:])
            msg_arrived_flag.set()
        elif msg[0] == msg_start_byte:
            received = str(msg[1:])
            for i in range(0,N):
                if file_name[i] == '.':
                    dot = i
            r_name = file_name[0:dot]
            r_ext = file_name[dot+1:]
            with open(r_name + ".zip", 'wb') as g:
                g.write(received)
            zfile = zipfile.ZipFile(r_name + ".zip")
            zfile.extract(file_name, path2)
            zfile.close()
            os.remove(r_name + ".zip")
        else:
            msg_arrived_flag.set()

# colocar aqui o diretório do arquivo usando barra dupla (\\)
path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
path2 = 'C:\\Users\\Usuário\\Desktop'
os.chdir(path)

sending = threading.Thread(target=send_file)
receiving = threading.Thread(target=receive_file)

sending.start()
receiving.start()



# simulando a recepção
##recebido_byte = bytearray(N)
##for i in range(0, N):
##    recebido_byte[i] = data_byte[i]
##
##recebido = str(recebido_byte)
##
##with open(name + "_saida.zip", 'wb') as g:
##    g.write(recebido)
##
##zfile = zipfile.ZipFile(name + "_saida.zip")
##zfile.extract(arq, path2)
##zfile.close()
##os.remove(name + "_saida.zip")


