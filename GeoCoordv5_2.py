#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os.path
""""
версия 5.1
для преобразования координат используется матрица преобразований 3х3  t
для определения цвета полностью проверяем квадрат от -TestAreaSize до +TestAreaSize
если отклонение всех компонент проверяемого цвета менее 10 - значи цвет совпал. Итоговый цвет- с наибольшим количесвтом 
совпадений
Для посика штриховки используем квадрат -TestAreaSize*2 до +TestAreaSize *2
сравниваем стандаттное отклонение пиеселей в горизонтальных и диагональных линиях
"""

from PIL import Image, ImageDraw
import numpy as np
import argparse


# класс для хранения данных цвета и его описания
class TColorLegend:
    def __init__(self, color=None, main_description='', project_decription=''):
        if color is None:
            color = [0, 0, 0]
        self.color = color
        self.color_cnt = 0  # число совпадений цвета
        self.main_description = main_description
        self.project_description = project_decription


# класс для хранения координаты точки, GPS или Pix, и описания к этой координате
class TMapCoord:
    def __init__(self, coord=None, text_coord='', main_description='', project_decription=''):
        if coord is None:
            coord = [0.0, 0.0]
        coord.append(1.0)
        self.coord = np.array(coord)  # массив с координатами float для GPS .третья координата =1 -служебная
        self.text_coord = text_coord
        self.is_gps = True

        self.main_description = main_description
        self.project_description = project_decription


# класс для хранения картинки
class TGeoPic:
    def __init__(self, pictfile):
        self.image = Image.open(pictfile)  # Открываем изображение.
        self.draw = ImageDraw.Draw(self.image)  # Создаем инструмент для рисования.
        self.width = self.image.size[0]  # Определяем ширину.
        self.height = self.image.size[1]  # Определяем высоту
        self.pix = self.image.load()  # Выгружаем значения пикселей.

    def __del__(self):
        del self.draw

    # отладочная функция . рисует на карте в нужном месте кружок
    def draw_point(self, x, y, size, color):
        if size < x < self.width - size and size < y < self.height - size:
            self.draw.ellipse((x - size, y - size, x + size, y + size), fill=color, outline=color)

    # отладочная функция . сохраняет карту (с нарисованными кружками)
    def save_pict(self, filename):
        self.image.save(filename)

    # возвращает цвет пикселя
    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pix[x, y]
        else:
            return None


# класс для преобразования координат GPS в пиксели и хранения конфигурационной
# информации карты
class TGeoMap:
    def __init__(self, config_file_name=''):
        # массив описаний цветов карты
        self.color_legends = []
        # матрица линейных преобразований координат
        self.rotate_matrix = np.eye(3)

        self.test_area_half_size = 10
        if config_file_name != '':
            self.load_geo_map(config_file_name)

    # конвертирует координаты из GPS в пиксели
    def convert_geo_coord(self, map_coord):
        for mcrd in map_coord:
            # умножение матрицы на вектор
            mcrd.coord = self.rotate_matrix.dot(mcrd.coord)
            mcrd.is_gps = False

    # загрузка конфигурации карты (и  программы)  из файла
    def load_geo_map(self, config_file):

        conf = {}
        file = open(config_file)
        # читаем конфигурационный файл построчно
        for line in file:
            if line[0].isalpha() and line.find(':') > 0:
                st = line.split(':')
                if st[0] == 'color':
                    # заполняем табл цветов
                    st1 = st[1].strip('\n\r ').split(';')
                    # заполняем координаты цвета и его описание
                    self.color_legends.append(TColorLegend(color=[int(st1[0]), int(st1[1]), int(st1[2])],
                                                           main_description=st1[3],
                                                           project_decription=st1[4]))

                else:
                    conf[st[0]] = st[1].strip("\n\r ").split(';')
        file.close()
        # матрица для расчета преобразования
        m = np.zeros((6, 6))
        # первое уравнение для Х1
        m[0][0] = float(conf['T1'][1])  # GPS1 2я коорд
        m[0][2] = float(conf['T1'][0])  # GPS1 1я коорд
        m[0][4] = 1.0
        # второе уравнение для Y1
        m[1][1] = float(conf['T1'][1])  # GPS1 2я коорд
        m[1][3] = float(conf['T1'][0])  # GPS1 1я коорд
        m[1][5] = 1.0
        # третье уравнение для X2
        m[2][0] = float(conf['T2'][1])  # GPS2 2я коорд
        m[2][2] = float(conf['T2'][0])  # GPS2 1я коорд
        m[2][4] = 1.0
        # четвертое уравнение для Y2
        m[3][1] = float(conf['T2'][1])  # GPS2 2я коорд
        m[3][3] = float(conf['T2'][0])  # GPS2 1я коорд
        m[3][5] = 1.0

        # пятое уравнение для X3
        m[4][0] = float(conf['T3'][1])  # GPS3 2я коорд
        m[4][2] = float(conf['T3'][0])  # GPS3 1я коорд
        m[4][4] = 1.0
        # шестое уравнние для Y3
        m[5][1] = float(conf['T3'][1])  # GPS3 2я коорд
        m[5][3] = float(conf['T3'][0])  # GPS3 1я коорд
        m[5][5] = 1.0
        # вектор с пикселями
        p = np.zeros(6)
        p[0] = float(conf['T1'][2])  # коорд х1 на картинке
        p[1] = float(conf['T1'][3])  # коорд y1 на картинке
        p[2] = float(conf['T2'][2])  # коорд х2 на картинке
        p[3] = float(conf['T2'][3])  # коорд y2 на картинке
        p[4] = float(conf['T3'][2])  # коорд х3 на картинке
        p[5] = float(conf['T3'][3])  # коорд y3 на картинке

        # решаем систему уравнений
        r = np.linalg.solve(m, p)

        # заполняем матрицу преобразования (нули и единицы там уже на своем месте)
        self.rotate_matrix[0][0] = r[0]
        self.rotate_matrix[0][1] = r[2]
        self.rotate_matrix[0][2] = r[4]
        self.rotate_matrix[1][0] = r[1]
        self.rotate_matrix[1][1] = r[3]
        self.rotate_matrix[1][2] = r[5]

        # test
        # testg = np.array((82.981385, 54.855265, 1.0))
        # testx = self.RotateMatrix.dot(testg)

        self.test_area_half_size = int(conf['TestAreaSize'][0])

    # функция находит ближайший подходящий цвет из массива цветов, заданных коф файлом
    # для этого перебираются все цвета, попавщие в квадра - 2size*2

    def get_color_info(self, image, x, y):
        #возвращаемое описание цвета
        color_info = ''
        #проверка допустимости координат
        if 0 < x < image.width and 0 < y <image.height:
            # собираем все пиксели в массив
            probe_colors = []
            # делаем проход по квадрату с ребров 2TestAreaSize
            for i in range(-self.test_area_half_size, self.test_area_half_size + 1):
                for j in range(-self.test_area_half_size, self.test_area_half_size + 1):
                    color = image.get_pixel(x + i, y + j)
                    if color is not None:
                        probe_colors.append(color)

            d_colors = []
            # проходим по массиву всех цветов из конфигурации
            # делаем расчет совпадений  для каждого цвета  (отклонение по каждой компоненте <10)
            for legend_color in self.color_legends:
                match_color_cnt = 0
                for probe_color in probe_colors:
                    if abs(probe_color[0] - legend_color.color[0]) < 10 and \
                            abs(probe_color[1] - legend_color.color[1]) < 10 and \
                            abs(probe_color[2] - legend_color.color[2]) < 10:
                        match_color_cnt += 1
                legend_color.color_cnt = match_color_cnt
                d_colors.append(legend_color)
            d_colors.sort(key=lambda c: c.color_cnt, reverse=True)

            # первый цвет  -самый подходящий (максимальное кол-во попаданий)
            color_info = d_colors[0].main_description + ';'
            # определение диагональной штриховки на области
            if self.is_hatched(image, x, y):
                color_info += 'Проект;'
            else:
                color_info += 'Существующий;'
            # добавляем колонку с резервным цветом
            color_info += d_colors[1].main_description + ';'
            # дополнительные колонки (вероятность 1, вероятность 2 , X,Y
            color_info += '{' + str(d_colors[0].color_cnt) + '/' + str(len(probe_colors)) + '};' \
                        + '{' + str(d_colors[1].color_cnt) + '/' + str(len(probe_colors)) + '};'


        else:
            color_info = 'Ошибка координат;;;;;'
        color_info += str(int(x)) + ';' + str(int(y))
        return color_info

    # основано на расчете дисперсии цвета по горизонтали и по диагонали
    def is_hatched(self, image, x, y):
        line_var = []  # дисперсия по линии
        r = []
        g = []
        b = []
        # горизонтальные линии
        for i in range(-self.test_area_half_size * 2, self.test_area_half_size * 2 + 1):
            r.clear()
            g.clear()
            b.clear()
            # получаем массивы цветов по строкам
            for j in range(-self.test_area_half_size * 2, self.test_area_half_size * 2 + 1):
                pix = image.get_pixel(x + i, y + j)
                r.append(pix[0])
                g.append(pix[1])
                b.append(pix[2])

            line_var.append(np.std(r))
            line_var.append(np.std(g))
            line_var.append(np.std(b))
        hor_var = np.std(line_var)
        if hor_var > 13:  # значит цвет неоднородный. Имеет смысл поискать штриховку
            line_var.clear()
            # диагональные линии
            for i in range(-self.test_area_half_size, 1):
                r.clear()
                g.clear()
                b.clear()
                for j in range(0, self.test_area_half_size + 1):
                    pix = image.get_pixel(x + i + j, y + i - j)
                    r.append(pix[0])
                    g.append(pix[1])
                    b.append(pix[2])
                line_var.append(np.std(r))
                line_var.append(np.std(g))
                line_var.append(np.std(b))
            diag_var = np.std(line_var)
            return diag_var < 0.4 * hor_var
        else:
            # Заведомо однородный цвет
            return False


def load_input_data(infile):
    # читаем файл запроса прострочно.
    # возвращаем массив из записей
    # 0 массив коорд точек [x,y]
    # 1 GPS координаты в текстовом виде
    # 2 поле для последующего ответа
    arr = []
    input_file = open(infile)
    for line in input_file:
        s0 = line.split(',')
        if len(s0) == 2:
            s1 = line.split(',')[0].strip('[ ]\n')
            s2 = line.split(',')[1].strip('[ ]\n')

            x = float(s2)
            y = float(s1)
            arr.append(TMapCoord(coord=[x, y], text_coord=line.strip(' \r\n')))

        else:
            print('ошибка формата', line)
    input_file.close()
    return arr


# процедура разбора командной строки
def create_parser():
    parser = argparse.ArgumentParser(description="Geo Location tool")
    parser.add_argument('-p', '--pict', default='PlanNovosib.jpg', help='Файл изображения карты')
    parser.add_argument('-c', '--conffile', default='geocoord.cfg', help='Альтернативный файл конфигурации')

    parser.add_argument('-i', '--inputfile', default='input.csv', help='Файл запроса с координатами точек')
    parser.add_argument('-o', '--outputfile', default='output.csv', help='Файл расшифровкики запроса')
    parser.add_argument('-d', '--debugfile', default='', help='Отображение в файле точек, переданных в запросе')
    return parser


if __name__ == '__main__':

    arg_parser = create_parser()
    namespace = arg_parser.parse_args()

    if os.path.exists(namespace.pict) \
            and os.path.exists(namespace.conffile) \
            and os.path.exists(namespace.inputfile):
        # пареметры конвертации GPS в пиксели
        gm = TGeoMap(namespace.conffile)
        # собственно картинка
        nvsb_pict = TGeoPic(namespace.pict)
        # точки из запросе
        geo_points = load_input_data(namespace.inputfile)
        # преобразовываем GPS в пиксели
        gm.convert_geo_coord(geo_points)

        # получаем информацию по точкам из запроса и пишем в выходной файл
        f = open(namespace.outputfile, 'w')
        for gp in geo_points:
            f.write(gp.text_coord + '; ' + gm.get_color_info(nvsb_pict, int(gp.coord[0]), int(gp.coord[1])) + '\n')
        f.close()


        # при необходимости сохраняем отладочную картинку
        if namespace.debugfile != '':
            for gp in geo_points:
                nvsb_pict.draw_point(int(gp.coord[0]), int(gp.coord[1]), 10, 'red')
            nvsb_pict.save_pict(namespace.debugfile)
    else:
        print('Нет файла', namespace.pict, '   или ', namespace.conffile, ' или ', namespace.inputfile)
