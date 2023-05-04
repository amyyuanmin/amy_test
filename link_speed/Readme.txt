link_speed_with_fio:
12hr fio:
pytest test_fio_link_speed.py --caseSuite=link_speed_fio --interval=0.05 --loop=66666 -s --junitxml=./fio_link_speed_result.xml
pytest test_fio_link_speed.py --caseSuite=link_speed_fio --interval=60 --loop=200 -s --junitxml=./fio_link_speed_result.xml
2hr fio:
pytest test_fio_link_speed.py --caseSuite=link_speed_2h --interval=0.05 --loop=66666 -s --junitxml=./fio_link_speed_result.xml
pytest test_fio_link_speed.py --caseSuite=link_speed_2h --interval=60 --loop=200 -s --junitxml=./fio_link_speed_result.xml


link_speed_idle:
pytest test_link_speed.py -s --interval=0.05 --loop=66666 --junitxml=./link_speed_result.xml
pytest test_link_speed.py -s --junitxml=./link_speed_result.xml

