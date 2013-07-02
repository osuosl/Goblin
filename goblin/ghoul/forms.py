from django.forms import Form, BooleanField


class StandInForm(Form):
    """
    Nothing special, just a place holder
    """

    pass


class TransitionForm(Form):
    """
    Step1B: Current Email Will Not Be Migrated
    """

    transition = BooleanField(required=True)
    migration = BooleanField(required=True)


class ProhibatedDataForm(Form):
    """
    Step2 No (also, Step2 Yes B)
    """

    accept = BooleanField(required=True)


class MobileAccessForm(Form):
    """
    Step3
    """

    reconfig = BooleanField(required=True)
    narcissism = BooleanField(required=True)


class ConfirmForm(Form):
    """
    Step4 Yes
    """

    prepared = BooleanField(required=True)
    no_access = BooleanField(required=True)
    no_delete = BooleanField(required=True)
    confirm_email = BooleanField(required=True)


class FinalConfirmForm(Form):
    """
    Step4 No (Also Step4 Yes B)
    """

    i_accept = BooleanField(required=True)
