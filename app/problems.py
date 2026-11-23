class DocketError(ValueError):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.status = code, status


LABEL = {
    'WIDTH':'表单列数错误','BLANK':'空白记录','TIMESTAMP':'时间戳无效','INTERVAL':'区间倒置',
    'UNKNOWN_BERTH':'泊位不存在','RANGE':'窗外记录','UNSET':'字段缺失','DUPLICATE':'重复记录',
    'ID_CONFLICT':'同编号冲突','PLATE':'车牌格式错误','BAD_STATUS':'预约状态无效',
    'PLATE_OVERLAP':'多个车在同一泊位','BERTH_OVERLAP':'同车同时出现在多个泊位',
    'FREE':'预约首免','BASE':'基础价','UPGRADE':'升级价','CANCELLED':'到达前预约撤销',
    'BOOKED':'预约已关联','WALK_IN':'无生效预约','GAP':'实收差价','MATCH':'实收一致',
    'NO_PAYMENT':'无实收回执','ORPHAN':'游离实收','ATTACH_CONFLICT':'预约版本冲突',
    'AMOUNT':'金额无效','UNKNOWN_SENSOR':'杆侧来源缺失','NONE':'无占位',
}
