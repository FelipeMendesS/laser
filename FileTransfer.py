# -*- coding: cp1252 -*-
import os
import zipfile
import threading
import serialData
import time
from struct import *

# colocar aqui o diretório do arquivo usando barra dupla (\\)
path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
path2 = 'C:\\Users\\Usuário\\Desktop'
os.chdir(path)

sending = threading.Thread(target=send_file)
receiving = threading.Thread(target=receive_file)

sending.start()
receiving.start()

# constantes do protocolo
send_request = bytearray([1])
send_ok = bytearray([2])

def send_file():
    ans = 's'
    msg_flag = False
    while ans == 's':
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
        send_data(msg)
        t0 = time.clock()
        while (time.clock()-to < 30):
            if not message_queue_is_empty():
                msg_flag = True
                break

        if msg_flag:
            msg = message_get()
            if msg == send_ok:
                send_data(data_byte)
                msg_flag = False
        

        ans = raw_input("Gostaria de enviar outro arquivo? (s/n): ")




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


