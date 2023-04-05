import os
from wsgiref.util import FileWrapper

import roman
from astro_plasma import Ionization
from django.http import HttpRequest, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView, View

from astrodata.utils import is_server_running, is_test_running

from .forms import PARMANU, InterpolateIonFractionForm, InterpolateMDForm

if is_server_running() or is_test_running():
    dataset_base_path = os.getenv('IONIZATION_DATASET_DIR')

    CHUNK_SIZE = int(os.getenv('DOWNLOAD_CHUNK_SIZE', 1 << 12))
    FILE_NAME_TEMPLATE = 'ionization.b_{:06d}.h5'


class InterpolationView(TemplateView):
    template_name = 'ionization/interpolation.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('action') is None:
            return redirect(request.path + '?action=ion_frac')
        kwargs['action'] = request.GET.get('action')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        match kwargs.get('action'):
            case 'ion_frac':
                kwargs['form'] = InterpolateIonFractionForm()
            case 'mass_density':
                kwargs['form'] = InterpolateMDForm()
        return super().get_context_data(**kwargs)

    def post(self, request: HttpRequest):
        action = request.GET.get('action')
        match action:
            case 'ion_frac':
                form = InterpolateIonFractionForm(request.POST)
            case 'mass_density':
                form = InterpolateMDForm(request.POST)
            case _:
                return redirect(request.path + '?action=ion_frac')

        if not form.is_valid():
            is_autofocus = False
            for name, field in form.fields.items():
                if name in form.errors:
                    field.widget.attrs = {
                        'class': f"{field.widget.attrs.get('class', '')} is-invalid".strip(),
                        'autofocus': 'true' if is_autofocus else 'false',
                    }
                    is_autofocus = True
            return render(request, self.template_name, {'form': form, 'action': action})

        interpolation_data = {}
        match action:
            case 'ion_frac':
                i = Ionization(dataset_base_path)

                interpolation_data['ion_frac'] = 10**i.interpolate_ion_frac(**form.cleaned_data)
                symbol = PARMANU.getElSymbol(form.cleaned_data['element'])
                roman_ion = roman.toRoman(form.cleaned_data['ion'])
                interpolation_data['ionized_symbol'] = f'{symbol}<sup>{roman_ion}</sup>'
            case 'mass_density':
                i = Ionization(dataset_base_path)

                form.cleaned_data['part_type'] = form.cleaned_data['species_type']
                del form.cleaned_data['species_type']

                print(form.cleaned_data)
                mean_mass = i.interpolate_mu(**form.cleaned_data)
                number_density = i.interpolate_num_dens(**form.cleaned_data)

                interpolation_data['mean_mass'] = mean_mass
                interpolation_data['number_density'] = number_density

                interpolation_data['mean_mass_symbol'] = '&mu;'
                interpolation_data['number_density_symbol'] = 'n'
                match form.cleaned_data['part_type']:
                    case 'ion':
                        interpolation_data['mean_mass_symbol'] += '<sub>i</sub>'
                        interpolation_data['number_density_symbol'] += '<sub>i</sub>'
                    case 'electron':
                        interpolation_data['mean_mass_symbol'] += '<sub>e</sub>'
                        interpolation_data['number_density_symbol'] += '<sub>e</sub>'

        return render(request, self.template_name,
                      {'form': form, 'action': action, 'interpolation': interpolation_data})
    """
    # def form_invalid(self, form: InterpolateForm):
    #     if self.request.GET.get('format') == 'json':
    #         errors = json.loads(form.errors.as_json())
    #         errors = {'errors': errors}
    #         return JsonResponse(data=errors, status=400)

    #     is_autofocus = False
    #     for name, field in form.fields.items():
    #         if name in form.errors:
    #             field.widget.attrs = {
    #                 'class': f"{field.widget.attrs.get('class', '')} is-invalid".strip(),
    #                 'autofocus': 'true' if is_autofocus else 'false',
    #             }
    #             is_autofocus = True

    #     return super().form_invalid(form)

    # def form_valid(self, form: InterpolateForm):
    #     ionization = Ionization(dataset_base_path)

    #     ion_frac = ionization.interpolate_ion_frac(nH=form.cleaned_data['nh'],
    #                                                temperature=form.cleaned_data['temperature'],
    #                                                metallicity=form.cleaned_data['metallicity'],
    #                                                redshift=form.cleaned_data['redshift'],
    #                                                mode=form.cleaned_data['mode'],
    #                                                element=form.cleaned_data['element'],
    #                                                ion=form.cleaned_data['ion'])
    #     mu_mass = ionization.interpolate_mu(nH=form.cleaned_data['nh'],
    #                                         temperature=form.cleaned_data['temperature'],
    #                                         metallicity=form.cleaned_data['metallicity'],
    #                                         redshift=form.cleaned_data['redshift'],
    #                                         mode=form.cleaned_data['mode'],
    #                                         part_type=form.cleaned_data['species_type'])
    #     nrho = ionization.interpolate_num_dens(nH=form.cleaned_data['nh'],
    #                                            temperature=form.cleaned_data['temperature'],
    #                                            metallicity=form.cleaned_data['metallicity'],
    #                                            mode=form.cleaned_data['mode'],
    #                                            redshift=form.cleaned_data['redshift'],
    #                                            part_type=form.cleaned_data['species_type'])

    #     interpolation = {
    #         'ion_frac': 10 ** ion_frac,
    #         'mu_mass': float(mu_mass),
    #         'number_density': float(nrho),
    #     }

    #     if self.request.GET.get('format') == 'json':
    #         return JsonResponse(data={'data': interpolation, 'request': form.cleaned_data})

    #     context = {'form': form,
    #                'interpolation': interpolation}
    #     return render(self.request, self.template_name, context)
"""


class DownloadFileView(View):
    def get(self, request, batch_id: int):
        target_file = dataset_base_path / FILE_NAME_TEMPLATE.format(batch_id)
        content = FileWrapper(open(target_file, 'rb'), CHUNK_SIZE)
        response = StreamingHttpResponse(content, content_type='application/x-hdf5')
        response['Content-Length'] = target_file.stat().st_size
        response['Content-Disposition'] = f'attachment; filename={target_file.name}'
        return response
