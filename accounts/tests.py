# from django.test import TestCase
# import math
# # Create your tests here.
#
# import datetime
# import time
#
# # atime = []
# # btime = []
# #
# # for _ in range(7):
# #     if _ % 2 == 0:
# #         atime.append(datetime.datetime.now())
# #     else:
# #         btime.append(datetime.datetime.now())
# #     time.sleep(3)
# #
# # print("atime = ", atime)
# # print("btime = ", btime)
#
#
# # def intervalscoring(atime, btime):
# def intervalscoring(self, atime, aanomalytype, btime, banomalytype):
#     # 92.53548129d/(diff.doubleValue()+7.37685567d)-2.432896244d
#     if not isinstance(atime, list): atime = [atime]
#     if not isinstance(btime, list): btime = [btime]
#
#     atime.sort()
#     btime.sort()
#
#     aValue = None
#     bValue = None
#     for _ in atime:
#         print("looking for value of a : ", _)
#         bList = [b for b in btime if b < _]
#         if bList:
#             aValue = _
#             bValue = bList.pop()
#             print("a : ", aValue, " b : ", bValue)
#             break
#
#     if aValue and bValue:
#         self.intervalscoretemp = abs(int((aValue - bValue).total_seconds()))
#         self.intervalscore = 0.3125656 + 9.642015 / (math.pow(2, self.intervalscoretemp / 11.42757))
#     else:
#         self.intervalscore = 0
#
#     return self.intervalscore
#
#     # if aValue and bValue:
#     #     intervalscoretemp = abs(int((aValue - bValue).total_seconds()))
#     #     intervalscore = 0.3125656 + 9.642015 / (math.pow(2, intervalscoretemp / 11.42757))
#     # else:
#     #     intervalscore = 0
#     #
#     # return intervalscore
#
#     # # if aanomalytype == 1:# or aanomalytype==2:
#     # #     atime = atime
#     # # if banomalytype==1:# or banomalytype ==2:
#     # #     btime = btime
#     # # if aanomalytype in (1201, 1301, 1203,1204,1303,1304,2):# or aanomalytype ==1301:
#     # #     atime= min(atime)
#     # # if banomalytype in (1201, 1301, 1203,1204,1303,1304,2):#==1201 or banomalytype ==1301:
#     # #     btime= min(btime)
#     # atime = min(atime)
#     # btime = min(btime)
#     # self.intervalscoretemp = abs(int((atime - btime).total_seconds()))
#     # #        self.intervalscore = 92.53548129/(self.intervalscoretemp + 7.37685567) -2.432896244
#     # self.intervalscore = 0.3125656 + 9.642015 / (math.pow(2, self.intervalscoretemp / 11.42757))
#     # return self.intervalscore
#
# if __name__ == "__main__":
#     atime = []
#     btime = []
#
#     for _ in range(7):
#         if _ % 2 == 0:
#             atime.append(datetime.datetime.now())
#         # else:
#         #     btime.append(datetime.datetime.now())
#         btime.append(datetime.datetime.now())
#         time.sleep(1)
#
#     atime.sort(reverse=True)
#     btime.sort(reverse=True)
#
#     print("atime = ", atime)
#     print("btime = ", btime)
#
#     val = intervalscoring(atime, btime)
#     print("Score : ", val)
