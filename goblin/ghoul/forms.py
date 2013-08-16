from django.forms import Form, BooleanField


class StandInForm(Form):
    """
    Nothing special, just a place holder
    """

    pass


class TransitionForm(Form):
    """
    Step1noB: Current Email Will Not Be Migrated
    """

    transition = BooleanField(required=True)


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

    no_access = BooleanField(required=True)
    no_delete = BooleanField(required=True)
    confirm_email = BooleanField(required=True)
    permanent = BooleanField(required=True)


class FinalConfirmForm(Form):
    """
    Step4 No (Also Step4 Yes B)
    """

    i_accept = BooleanField(required=True)

FORMS = [("migrate", StandInForm),
         ("confirm_trans", TransitionForm),
         ("forward_notice", StandInForm),
         ("prohibit", ProhibatedDataForm),
         ("mobile", MobileAccessForm),
         ("confirm", StandInForm)]
