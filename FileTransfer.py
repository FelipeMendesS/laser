# -*- coding: cp1252 -*-
import os
import zipfile
import threading
from struct import *
import serialData

# colocar aqui o diretório do arquivo usando barra dupla (\\)
path = 'C:\\Users\\Usuário\\Desktop\\ITA\\ELE\\4º Semestre\\Projeto EEA-47\\Leitura_Arquivos'
path2 = 'C:\\Users\\Usuário\\Desktop'
os.chdir(path)

def send_file():
    ans = 's'
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

        msg = bytearray([1]) + N_byte + bytearray(arq)
        

        ans = raw_input("Gostaria de enviar outro arquivo? (s/n): ")



----------------------------------------------------------------
# simulando a recepção
recebido_byte = bytearray(N)
for i in range(0, N):
    recebido_byte[i] = data_byte[i]

recebido = str(recebido_byte)

with open(name + "_saida.zip", 'wb') as g:
    g.write(recebido)

zfile = zipfile.ZipFile(name + "_saida.zip")
zfile.extract(arq, path2)
zfile.close()
os.remove(name + "_saida.zip")
