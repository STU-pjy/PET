import sys
import os
import random
import json
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QBrush
from openai import OpenAI
from PyQt5.QtCore import QThread, pyqtSignal


# 启用软件OpenGL渲染（解决显卡兼容问题）
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseSoftwareOpenGL)

FAVOR_REWARDS = {
    'exercise': 3,    # 完成运动
    'transform': 5,   # 完成学习
    'pipi': 4,        # 完成工作
    'eating': 2,      # 成功进食
    'clone': -10       # 分身消耗好感
}

class FavorabilityManager:
    CONFIG_PATH = Path.home() / ".deskpet_config.json"

    @classmethod
    def load_favorability(cls):
        try:
            with open(cls.CONFIG_PATH, 'r') as f:
                return 100
                #return json.load(f).get('favorability', 0)
        except (FileNotFoundError, json.JSONDecodeError):
            return 100  # 默认值

    @classmethod
    def save_favorability(cls, value):
        config = {'favorability': max(0, value)}  # 保证不低于0
        with open(cls.CONFIG_PATH, 'w') as f:
            json.dump(config, f)

class DeskPet(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        print("[DEBUG] 宠物对象已创建")  # DEBUG: 对象创建检测
        self.childPets = []
        self.isDragging = False
        self.change = False
        self.initUI()
        self.favorability = FavorabilityManager.load_favorability()

    def initUI(self):
        # 临时测试背景色（注释掉透明背景）
        #self.setStyleSheet("background-color: rgba(255,0,0,100);")
        # 确保窗口属性设置正确


        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setGeometry(100, 100, 1000, 1000)  # DEBUG: 移动到屏幕左上角
        print(f"[DEBUG] 窗口初始位置：{self.geometry()}")

        self.currentAction = self.startIdle
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)

        self.startIdle()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self.setMouseTracking(True)
        self.dragging = False

    def showEvent(self, event):
        """DEBUG: 窗口显示事件检测"""
        print("[DEBUG] 窗口已显示")
        super().showEvent(event)

    def loadImages(self, path):
        """增强版图片加载（带错误处理）"""
        try:
            # DEBUG: 路径存在性检查
            if not os.path.exists(path):
                QtWidgets.QMessageBox.critical(self, "路径错误", f"目录不存在：\n{path}")
                return []

            # DEBUG: 图片文件检测
            files = [f for f in os.listdir(path) if f.lower().endswith('.png')]
            print(f"[DEBUG] 在 {path} 中找到 {len(files)} 张PNG图片")

            if not files:
                QtWidgets.QMessageBox.critical(self, "图片错误", "目录中没有PNG文件")
                return []

            # DEBUG: 图片加载验证
            images = []
            for f in files:
                img_path = os.path.join(path, f)
                pixmap = QtGui.QPixmap(img_path)
                if pixmap.isNull():
                    print(f"[WARNING] 加载失败：{img_path}")
                    continue
                images.append(pixmap)

            if not images:
                QtWidgets.QMessageBox.critical(self, "图片错误", "所有PNG文件加载失败")

            return images

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "加载错误", f"发生异常：\n{str(e)}")
            return []

    # def updateAnimation(self):
    #     """增强版动画更新（适配大尺寸图片）"""
    #     if not self.images:
    #         print("[WARNING] 没有可用的动画帧")
    #         return
    #
    #     try:
    #         # 获取当前窗口尺寸
    #         window_size = self.size()
    #
    #         # 动态缩放图片
    #         scaled_pix = self.images[self.currentImage].scaled(
    #             window_size,
    #             QtCore.Qt.KeepAspectRatio,
    #             QtCore.Qt.SmoothTransformation
    #         )
    #
    #         # 创建透明画布
    #         canvas = QtGui.QPixmap(window_size)
    #         canvas.fill(QtCore.Qt.transparent)
    #
    #         # 居中绘制
    #         painter = QtGui.QPainter(canvas)
    #         painter.drawPixmap(
    #             (window_size.width() - scaled_pix.width()) // 2,
    #             (window_size.height() - scaled_pix.height()) // 2,
    #             scaled_pix
    #         )
    #         painter.end()
    #
    #         self.setPixmap(canvas)
    #         print(
    #             f"[动画] 显示第 {self.currentImage} 帧 | 原始尺寸: {self.images[self.currentImage].size()} | 缩放后: {scaled_pix.size()}")
    #
    #         self.currentImage = (self.currentImage + 1) % len(self.images)
    #
    #     except Exception as e:
    #         print(f"[ERROR] 动画更新失败: {str(e)}")
    #
    #     self.repaint()


    #  ========= 菜单 ======================================================================================

    def showMenu(self, position):
        menu = QtWidgets.QMenu()
        favor_action = menu.addAction(f"当前好感度: {self.favorability} ❤")
        favor_action.setEnabled(False)

        # 根据当前状态动态添加菜单项
        if self.currentAction == self.sleep:
            menu.addAction("唤醒", self.WakeUp)
        elif self.currentAction == self.transform:
            menu.addAction("停止学习", self.stopLearning)
        elif self.currentAction == self.pipi:
            menu.addAction("结束上班", self.stopWork)
        elif self.currentAction == self.exercise:  # 新增运动状态判断
            menu.addAction("停止运动", self.stopExercise)  # 运动状态专属菜单
        else:
            menu.addAction("运动", self.exercise)
            menu.addAction("吃饭", self.eating)
            menu.addAction("睡觉", self.sleep)
            menu.addAction("上班", self.pipi)
            menu.addAction("分身术", self.clonePet)
            menu.addAction("学习", self.transform)

        # 公共菜单项
        child_menu = menu.addMenu("小彩蛋")
        child_menu.addAction("开发者的Q/A", self.starttalk)
        # child_menu.addAction("小游戏", self.transform)
        menu.addSeparator()
        menu.addAction("开始聊天", self.start_chat)  # 新增聊天入口
        menu.addAction("停止", self.startIdle)
        menu.addAction("隐藏", self.minimizeWindow)
        menu.addAction("退出", self.gracefulExit)  # 修改原有退出按钮连接

        menu.exec_(self.mapToGlobal(position))

    #  ========= 零食，已被注释 ==============================================================================
    def Snack(self):
        self.setFixedSize(1000, 1000)
        self.currentAction = self.sleep
        self.images = self.loadImages(r"D:\数据科学与大数据技术\大二下课程\数据分析与应用\final\all_pet\pet\vup\Eat\Happy\back_lay")
        self.currentImage = 0
        self.timer.start(100)
        QtCore.QTimer.singleShot(len(self.images) * 100, self.sleep)

    #  ========= 待机动画 ==================================================================================

    def startIdle(self):
        """待机动画（首次播放启动动画）"""
        # 初始化首次运行标记
        if not hasattr(self, 'is_first_idle'):
            self.is_first_idle = True
            self.startup_played = False  # 新增启动动画播放状态标记

        # 首次运行加载启动动画
        if self.is_first_idle and not self.startup_played:
            print("[DEBUG] 首次进入待机，播放启动动画")
            # startup_path = r"E:\Game\Steam\steamapps\common\VPet\mod\0000_core\pet\vup\StartUP\Happy_1"
            startup_path = r"mod\0000_core\pet\vup\StartUP\Happy"
            startup_images = self.loadImages(startup_path)

            if startup_images:
                # 临时替换为启动动画
                self.images = startup_images
                self.currentImage = 0
                self.timer.start(100)

                # 设置单次播放完成回调
                QtCore.QTimer.singleShot(
                    len(self.images) * 100,
                    self.finishStartupAnimation
                )
                self.startup_played = True  # 标记已播放
                return
            else:
                print("[WARNING] 启动动画加载失败，直接进入正常待机")

        # 正常待机资源加载（原有逻辑）
        path = r"mod\0000_core\pet\vup\BDay\B"
        self.images = self.loadImages(path)

        if not self.images:
            print("[DEBUG] 使用备用测试图像")
            self.images = [QtGui.QPixmap(100, 100) for _ in range(4)]
            for i, pixmap in enumerate(self.images):
                pixmap.fill(QtGui.QColor(i * 50, i * 50, i * 50))

        # 初始化动画参数
        self.setFixedSize(1000, 1000)
        self.currentAction = self.startIdle
        self.currentImage = 0
        self.timer.start(100)
        self.is_first_idle = False  # 标记已完成首次运行
        print("[DEBUG] 已启动待机动画")

    def finishStartupAnimation(self):
        """启动动画播放完成回调"""
        print("[DEBUG] 启动动画播放完成，切换到正常待机")
        self.timer.stop()
        self.startIdle()  # 重新调用以加载正常待机动画

    def stopOtherActions(self):
        self.timer.stop()
        self.startIdle()

    #  ========= 学习 ======================================================================================

    def transform(self):
        """学习动作（分三个阶段）"""
        if not hasattr(self, 'transform_stage'):
            self.transform_stage = 0  # 初始化学习阶段标记

        stage_paths = [
            r"mod\0000_core\pet\vup\WORK\Study\A_Nomal",  # 阶段0：开始学习
            r"mod\0000_core\pet\vup\WORK\Study\B_1_Nomal",  # 阶段1：持续学习
            r"mod\0000_core\pet\vup\WORK\Study\C_Nomal"  # 阶段2：结束学习
        ]

        self.setFixedSize(1000, 1000)
        self.currentAction = self.transform
        self.images = self.loadImages(stage_paths[self.transform_stage])

        if not self.images:
            print(f"[ERROR] 学习阶段{self.transform_stage}资源加载失败")
            return

        self.currentImage = 0
        self.timer.start(70)

        # 统一阶段控制逻辑
        if self.transform_stage == 0:
            QtCore.QTimer.singleShot(
                len(self.images) * 70,
                lambda: self.setTransformStage(1)
            )
        elif self.transform_stage == 1:
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(self.transformLoopAnimation)
        else:
            QtCore.QTimer.singleShot(
                len(self.images) * 70,
                self.finishTransform
            )

    def setTransformStage(self, stage):
        """设置学习阶段"""
        self.transform_stage = stage
        self.currentImage = 0  # 重置帧计数器
        self.transform()

    def transformLoopAnimation(self):
        """学习循环动画"""
        try:
            self.currentImage = (self.currentImage + 1) % len(self.images)
            scaled_pix = self.images[self.currentImage].scaled(
                self.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pix)
        except Exception as e:
            print(f"[TRANSFORM ERROR] {str(e)}")
            self.stopLearning()

    def finishTransform(self):
        """结束学习"""
        self.timer.stop()
        self.transform_stage = 0
        self.startIdle()
        self._update_favorability('transform')  # 新增

    def stopLearning(self):
        """中断学习"""
        if self.currentAction == self.transform:
            if self.transform_stage == 1:
                self.timer.timeout.disconnect()
                self.timer.timeout.connect(self.updateAnimation)
                self.setTransformStage(2)
            else:
                self.timer.stop()
                self.startIdle()

    #  ========= 工作 ======================================================================================

    def pipi(self):
        """上班动作（分三个阶段）"""
        if not hasattr(self, 'work_stage'):
            self.work_stage = 0  # 初始化上班阶段标记

        stage_paths = [
            r"mod\0000_core\pet\vup\WORK\WorkTWO\A_Nomal",  # 阶段0：上班开始
            r"mod\0000_core\pet\vup\WORK\WorkTWO\B_2_Nomal",  # 阶段1：上班进行
            r"mod\0000_core\pet\vup\WORK\WorkTWO\C_Nomal"     # 阶段2：上班结束
        ]

        self.setFixedSize(1000, 1000)
        self.currentAction = self.pipi
        self.images = self.loadImages(stage_paths[self.work_stage])

        if not self.images:
            print(f"[ERROR] 上班阶段{self.work_stage}资源加载失败")
            return

        self.currentImage = 0
        self.timer.start(100)

        # 阶段控制逻辑
        if self.work_stage == 0:
            # 第一阶段：播放完毕后自动进入第二阶段
            QtCore.QTimer.singleShot(
                len(self.images) * 100,
                lambda: self.setWorkStage(1)
            )
        elif self.work_stage == 1:
            # 第二阶段：持续循环工作动画
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(
                lambda: self.workLoopAnimation()
            )
        # elif self.work_stage == 2:
        #     # 确保使用标准动画更新
        #     self.timer.timeout.disconnect()
        #     self.timer.timeout.connect(self.updateAnimation)
        else:
            # 第三阶段：播放完毕后返回待机
            QtCore.QTimer.singleShot(
                len(self.images) * 100,
                self.finishWork
            )

    def setWorkStage(self, stage):
        """修复版阶段切换"""
        self.work_stage = stage
        # 重置动画计数器
        self.currentImage = 0
        # 重新加载资源
        self.pipi()

    def workLoopAnimation(self):
        """工作循环动画"""
        try:
            self.currentImage = (self.currentImage + 1) % len(self.images)
            self.setPixmap(self.images[self.currentImage])
        except Exception as e:
            print(f"[ERROR] 工作动画错误: {str(e)}")

    def finishWork(self):
        """结束工作"""
        self.timer.stop()
        self.work_stage = 0  # 重置阶段标记
        self.startIdle()
        self._update_favorability('pipi')  # 新增

    def stopWork(self):
        """修复版中断工作方法"""
        if self.currentAction == self.pipi:
            if self.work_stage == 1:
                # 停止当前动画循环
                self.timer.timeout.disconnect()
                # 重要：重新连接标准动画更新
                self.timer.timeout.connect(self.updateAnimation)
                # 强制刷新阶段状态
                self.setWorkStage(2)
            else:
                self.timer.stop()
                self.startIdle()

    #  ========= 运动 =====================================================================================

    def exercise(self):
        """运动动作（分三个阶段）"""
        if not hasattr(self, 'exercise_stage'):
            self.exercise_stage = 0  # 初始化运动阶段标记

        stage_paths = [
            r"mod\0000_core\pet\vup\WORK\RopeSkipping\Happy\A",  # 阶段0：开始跳绳
            r"mod\0000_core\pet\vup\WORK\RopeSkipping\Happy\B\1",  # 阶段1：持续跳绳
            r"mod\0000_core\pet\vup\WORK\RopeSkipping\Happy\C"     # 阶段2：结束跳绳
        ]

        self.setFixedSize(1000, 1000)
        self.currentAction = self.exercise
        self.images = self.loadImages(stage_paths[self.exercise_stage])

        if not self.images:
            print(f"[ERROR] 运动阶段{self.exercise_stage}资源加载失败")
            return

        self.currentImage = 0
        self.timer.start(100)

        # 阶段控制逻辑
        if self.exercise_stage == 0:
            # 第一阶段：播放完毕后自动进入第二阶段
            QtCore.QTimer.singleShot(
                len(self.images) * 100,
                lambda: self.setExerciseStage(1)
            )
        elif self.exercise_stage == 1:
            # 第二阶段：持续循环运动动画
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(
                lambda: self.exerciseLoopAnimation()
            )
        else:
            # 第三阶段：播放完毕后返回待机
            QtCore.QTimer.singleShot(
                len(self.images) * 100,
                self.finishExercise
            )

    def setExerciseStage(self, stage):
        """设置运动阶段"""
        self.exercise_stage = stage
        self.currentImage = 0
        self.exercise()

    def exerciseLoopAnimation(self):
        """运动循环动画"""
        try:
            self.currentImage = (self.currentImage + 1) % len(self.images)
            scaled_pix = self.images[self.currentImage].scaled(
                self.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pix)
        except Exception as e:
            print(f"[EXERCISE ERROR] {str(e)}")
            self.stopExercise()

    def finishExercise(self):
        """结束运动"""
        self.timer.stop()
        self.exercise_stage = 0  # 重置阶段标记
        self.startIdle()
        self._update_favorability('exercise')  # 新增

    def stopExercise(self):
        """中断运动"""
        if self.currentAction == self.exercise:
            if self.exercise_stage == 1:  # 如果在运动阶段
                self.timer.timeout.disconnect()
                self.timer.timeout.connect(self.updateAnimation)
                self.setExerciseStage(2)  # 进入结束阶段
            else:
                self.timer.stop()
                self.startIdle()

    #  ========= 吃东西 ==================================================================================

    def eating(self):
        self.setFixedSize(1000, 1000)
        self.currentAction = self.eating
        self.images = self.loadImages(r"mod\0000_core\pet\vup\Eat\Nomal\back_lay")
        self.currentImage = 0
        self.timer.start(100)
        QtCore.QTimer.singleShot(len(self.images) * 100, self.startIdle)

    #  ========= 睡觉 ===================================================================================

    def sleep(self):
        """睡眠动作（分两个阶段）"""
        if not hasattr(self, 'sleep_stage'):
            self.sleep_stage = 0  # 初始化睡眠阶段标记

        stage_paths = [
            r"mod\0000_core\pet\vup\Sleep\A_Happy",  # 阶段0：入睡动画
            r"mod\0000_core\pet\vup\Sleep\B_Nomal"  # 阶段1：持续睡眠
        ]

        self.setFixedSize(1000, 1000)
        self.currentAction = self.sleep
        self.images = self.loadImages(stage_paths[self.sleep_stage])

        if not self.images:
            print(f"[ERROR] 睡眠阶段{self.sleep_stage}资源加载失败")
            return

        self.currentImage = 0
        self.timer.start(100)

        # 阶段控制逻辑
        if self.sleep_stage == 0:
            # 播放完A_Happy后自动进入B_Nomal
            QtCore.QTimer.singleShot(
                len(self.images) * 100,
                lambda: self.setSleepStage(1)
            )
        else:
            # B_Nomal阶段持续循环
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(
                lambda: self.sleepLoopAnimation()
            )

    def setSleepStage(self, stage):
        """设置睡眠阶段"""
        self.sleep_stage = stage
        self.sleep()

    def sleepLoopAnimation(self):
        """持续睡眠动画更新"""
        try:
            self.setPixmap(self.images[self.currentImage])
            self.currentImage = (self.currentImage + 1) % len(self.images)
        except IndexError:
            print(f"[ERROR] 无效的帧索引：{self.currentImage}/{len(self.images)}")
        self.repaint()

    def stopOtherActions(self):
        if self.currentAction == self.sleep:
            self.sleep_stage = 0  # 新增重置标记
            self.timer.timeout.disconnect()
            self.timer.timeout.connect(self.updateAnimation)
            self.timer.stop()
            self.startIdle()
        else:
            self.timer.stop()
            self.startIdle()

    def WakeUp(self):
        self.setFixedSize(1000, 1000)
        self.images = self.loadImages(
            r"mod\0000_core\pet\vup\Sleep\C_PoorCondition")
        self.currentImage = 0
        self.timer.start(130)
        QtCore.QTimer.singleShot(len(self.images) * 130, self.finishWakeUp)

    def finishWakeUp(self):
        """唤醒完成时重置阶段标记"""
        self.timer.stop()
        self.sleep_stage = 0  # 新增重置标记
        self.startIdle()

    #  ========= 退出程序 ===============================================================================

    def gracefulExit(self):
        """优雅退出方法（修复版）"""
        # 加载关机动画资源
        shutdown_path = r"mod\0000_core\pet\vup\Shutdown\Happy_1"
        self.shutdown_images = self.loadImages(shutdown_path)

        if not self.shutdown_images:
            print("[WARNING] 关机动画加载失败，直接退出")
            self.close()
            return

        # 重置动画参数
        self.currentAction = self.gracefulExit
        self.currentImage = 0
        self.images = []  # 清空常规动画帧

        # 禁用用户交互
        self.setEnabled(False)

        # 启动定时器（使用原有timer实例）
        self.timer.start(100)

    def forceClose(self):
        """强制关闭程序"""
        self.timer.stop()
        self.close()

    #  ========= 好感度 ===========
    def _update_favorability(self, action_type):
        delta = FAVOR_REWARDS.get(action_type, 0)
        self.favorability += delta
        # 实时保存到文件
        FavorabilityManager.save_favorability(self.favorability)

        # 好感度变化提示
        if delta != 0:
            self.show_favor_effect(delta)

    def show_favor_effect(self, delta):
        effect = QtWidgets.QLabel(self)
        effect.setText(f"{'+' if delta > 0 else ''}{delta}❤")
        effect.setStyleSheet("color: #FF69B4; font-size: 20px; font-weight: bold;")
        effect.move(self.width() // 2, 20)

        # 动画效果
        anim = QtCore.QPropertyAnimation(effect, b"pos")
        anim.setDuration(1000)
        anim.setStartValue(effect.pos())
        anim.setEndValue(QtCore.QPoint(effect.x(), effect.y() - 50))
        anim.finished.connect(effect.deleteLater)
        anim.start()

    #  ========= 分身 ===================================================================================

    def clonePet(self):
        if self.favorability >= 5:  # 分身需要5点好感
            new_pet = DeskPet()
            self.childPets.append(new_pet)
            new_pet.show()
            self._update_favorability('clone')
        else:
            QtWidgets.QMessageBox.warning(self, "提示", "好感度不足5点，无法创建分身！")

    #  ========= 其他 ===================================================================================

    def starttalk(self):
        starttalk = ChatApp()
        starttalk.show()
        self.childPets.append(starttalk)

    def closeEvent(self, event):
        FavorabilityManager.save_favorability(self.favorability)
        for child in self.childPets:
            child.close()
        super().closeEvent(event)

    def minimizeWindow(self):
        self.showMinimized()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.pos()
            self.prevAction = self.currentAction
            event.accept()

    def mouseMoveEvent(self, event):
        if QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            event.accept()

    def updateAnimation(self):
        """增强版动画更新（兼容关机动画）"""
        # 空值保护
        if not self.images and self.currentAction != self.gracefulExit:
            print("[WARNING] 没有可用的动画帧")
            return

        try:
            # 关机动画特殊处理
            if self.currentAction == self.gracefulExit and hasattr(self, 'shutdown_images'):
                if self.currentImage >= len(self.shutdown_images):
                    return

                # 动态缩放处理
                scaled_pix = self.shutdown_images[self.currentImage].scaled(
                    self.size(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )

                # 创建透明画布
                canvas = QtGui.QPixmap(self.size())
                canvas.fill(QtCore.Qt.transparent)

                # 居中绘制
                painter = QtGui.QPainter(canvas)
                painter.drawPixmap(
                    (self.width() - scaled_pix.width()) // 2,
                    (self.height() - scaled_pix.height()) // 2,
                    scaled_pix
                )
                painter.end()

                self.setPixmap(canvas)
                self.currentImage += 1

                # 播放完毕自动关闭
                if self.currentImage >= len(self.shutdown_images):
                    self.timer.stop()
                    self.close()

            # 其他动画正常处理流程
            else:
                window_size = self.size()

                # 动态缩放图片
                scaled_pix = self.images[self.currentImage].scaled(
                    window_size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )

                # 创建透明画布
                canvas = QtGui.QPixmap(window_size)
                canvas.fill(QtCore.Qt.transparent)

                # 居中绘制
                painter = QtGui.QPainter(canvas)
                painter.drawPixmap(
                    (window_size.width() - scaled_pix.width()) // 2,
                    (window_size.height() - scaled_pix.height()) // 2,
                    scaled_pix
                )
                painter.end()

                self.setPixmap(canvas)
                self.currentImage = (self.currentImage + 1) % len(self.images)

        except IndexError as e:
            print(f"[ERROR] 无效的帧索引：{self.currentImage}/{len(self.images) if self.images else 0}")
        except Exception as e:
            print(f"[ERROR] 动画更新失败: {str(e)}")
            if self.currentAction == self.gracefulExit:
                self.close()

        self.repaint()

    def start_chat(self):
        """启动聊天窗口"""
        chat_window = AIPetChatWindow(self)  # 传入当前实例
        chat_window.show()
        self.childPets.append(chat_window)


# --- API入口（修改版）---

# 在文件顶部新增以下类
class APIWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, system_prompt, user_input):
        super().__init__()
        self.system_prompt = system_prompt
        self.user_input = user_input

    def run(self):
        try:
            client = OpenAI(
                api_key="sk-8a7ae85179684482ac03af2505166c50",
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": self.user_input}
                ]
            )
            self.finished.emit(response.choices[0].message.content)
        except Exception as e:
            self.error.emit(str(e))

# --- AI聊天窗口（修改版）---
class AIPetChatWindow(QtWidgets.QMainWindow):
    def __init__(self, parent_pet):
        super().__init__()
        self.parent_pet = parent_pet  # 引用父级桌宠实例
        self.thread = None  # 新增线程引用
        self.init_ui()

    def init_ui(self):
        # 窗口设置
        self.setWindowTitle("AI 宠物聊天室")
        self.setGeometry(100, 100, 800, 600)

        # 使用桌宠同款背景
        bg_path = "mod/background.jpg"  # 替换实际路径
        self.background = QPixmap(bg_path).scaled(800, 600)
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(self.background))
        self.setPalette(palette)

        # 主布局
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        layout = QtWidgets.QVBoxLayout(main_widget)

        # 聊天记录显示
        self.chat_history = QtWidgets.QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            background: rgba(255,255,255,0.8); 
            border-radius: 10px; 
            padding: 15px;
            font-size: 50px;
        """)
        layout.addWidget(self.chat_history)

        # 输入区域
        input_widget = QtWidgets.QWidget()
        input_layout = QtWidgets.QHBoxLayout(input_widget)

        self.user_entry = QtWidgets.QLineEdit()
        self.user_entry.setPlaceholderText("输入消息...")
        self.user_entry.setStyleSheet("""
            background: white;
            border: 2px solid #cccccc;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        """)
        input_layout.addWidget(self.user_entry)

        self.send_btn = QtWidgets.QPushButton("发送")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(input_widget)

    def get_system_prompt(self):
        """动态获取基于当前好感度的系统提示"""
        favor = self.parent_pet.favorability
        if favor < 30:
            return "你是一只高冷的猫咪，名字叫小橘。你的回应简短冷淡，偶尔用'喵'回答。"
        elif 30 <= favor < 70:
            return "你是友好的猫咪小橘，会积极回应主人，语气温和。"
        else:
            return "你是活泼的猫咪小橘，喜欢用~喵喵~和颜文字（如~ o(*￣▽￣*)ブ~），经常撒娇！"

    def send_message(self):
        user_input = self.user_entry.text().strip()
        if not user_input:
            return

        # 禁用输入组件防止重复发送
        self.user_entry.setEnabled(False)
        self.send_btn.setEnabled(False)

        # 显示用户消息
        self._append_message("你", user_input, "#4CAF50")

        # 创建后台工作线程
        self.thread = QtCore.QThread()
        self.worker = APIWorker(
            system_prompt=self.get_system_prompt(),
            user_input=user_input
        )
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.worker.finished.connect(self.on_api_success)
        self.worker.error.connect(self.on_api_error)
        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        # 启动线程
        self.thread.start()


    def on_api_success(self, response):
        """处理成功响应"""
        self._append_message("小橘", response, "#2196F3")
        self._update_favorability()
        self.cleanup_thread()

    def on_api_error(self, error_msg):
        """处理错误"""
        ai_response = f"出错了喵~ ({error_msg})"
        self._append_message("小橘", ai_response, "#2196F3")
        self.cleanup_thread()

    def cleanup_thread(self):
        """清理线程资源"""
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.user_entry.clear()
        self.user_entry.setEnabled(True)
        self.send_btn.setEnabled(True)

    def _append_message(self, sender, text, color):
        html = f"""
        <div style='margin: 10px;'>
            <div style='color: {color}; font-weight: bold;'>{sender}:</div>
            <div style='background: rgba(255,255,255,0.9); 
                        border-radius: 8px; 
                        padding: 8px;
                        margin-top: 5px;'>
                {text}
            </div>
        </div>
        """
        self.chat_history.append(html)

    def _update_favorability(self):
        """每次对话增加1点好感度"""
        self.parent_pet.favorability += 1
        FavorabilityManager.save_favorability(self.parent_pet.favorability)


# 菜蛋APP
class ChatApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('聊天窗口')
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("你好，我是开发者”乐子猪“\n请问你想问什么？\n（该聊天的内容不完善且功能有缺陷）")
        layout.addWidget(label)

        button1 = QtWidgets.QPushButton("开发者你是哪里人呀？")
        button1.clicked.connect(self.on_button1_clicked)
        layout.addWidget(button1)

        button2 = QtWidgets.QPushButton("开发者你是一个什么样的人呀？")
        button2.clicked.connect(self.on_button2_clicked)
        layout.addWidget(button2)

        self.setLayout(layout)

    def on_button1_clicked(self):
        QtWidgets.QMessageBox.information(self, "回答", "我是广东人，现在住在上海！")

    def on_button2_clicked(self):
        QtWidgets.QMessageBox.information(self, "回答", "喜欢写代码和吃甜筒的普通人~")


# ... 保持原有聊天窗口代码不变 ...

if __name__ == "__main__":
    # DEBUG: 屏幕信息检测
    app = QtWidgets.QApplication(sys.argv)
    screen = QtWidgets.QDesktopWidget().screenGeometry()
    print(f"[DEBUG] 主屏幕尺寸：{screen.width()}x{screen.height()}")

    pet = DeskPet()
    pet.show()

    # DEBUG: 延迟检查窗口状态
    QtCore.QTimer.singleShot(1000, lambda:
    print(f"[DEBUG] 当前窗口状态：可见={pet.isVisible()} 激活={pet.isActiveWindow()}"))

    sys.exit(app.exec_())